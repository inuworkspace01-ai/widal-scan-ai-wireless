import os, uuid
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import httpx, numpy as np, cv2
load_dotenv()
SIMULATION=os.getenv("SIMULATION_MODE","true").lower()=="true"
ESP32=os.getenv("ESP32_BASE_URL","http://192.168.50.20").rstrip("/")
CAPTURE_DIR=Path(os.getenv("CAPTURE_DIR","runtime/captures")); CAPTURE_DIR.mkdir(parents=True,exist_ok=True)
captures={}
app=FastAPI(title="WIDAL-SCAN Local Bridge",version="0.1.0")
origins=[x.strip() for x in os.getenv("ALLOWED_ORIGINS","http://localhost:3000").split(",") if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,allow_methods=["GET","POST","DELETE"],allow_headers=["Content-Type","X-Bridge-Token"])
class WifiConfig(BaseModel):
 ssid:str=Field(min_length=1,max_length=32); password:str=Field(min_length=8,max_length=63); device_ip:str
@app.get("/v1/health")
def health(): return {"ok":True,"service":"widal-bridge","simulation":SIMULATION,"device":{"connected":False,"ip":ESP32,"name":"ESP32-CAM (pending)"}}
@app.get("/v1/device/status")
async def device_status():
 try:
  async with httpx.AsyncClient(timeout=2.5) as c:
   r=await c.get(f"{ESP32}/status"); r.raise_for_status(); return {"connected":True,"ip":ESP32,"details":r.json()}
 except Exception: return {"connected":False,"ip":ESP32,"message":"Device not reachable"}
@app.post("/v1/device/configure")
def configure_device(cfg:WifiConfig):
 if SIMULATION: return {"accepted":True,"simulation":True,"message":"Local request received; device provisioning is not implemented."}
 raise HTTPException(501,"Authenticated firmware provisioning is not implemented for this board.")
@app.post("/v1/capture")
async def capture():
 cid=str(uuid.uuid4())
 if SIMULATION:
  img=np.full((720,1100,3),245,dtype=np.uint8); cv2.rectangle(img,(30,30),(1070,690),(190,200,205),3)
  cv2.putText(img,"SIMULATION PREVIEW",(280,320),cv2.FONT_HERSHEY_SIMPLEX,1.7,(70,90,110),3)
  cv2.putText(img,"NOT A WIDAL SPECIMEN",(300,385),cv2.FONT_HERSHEY_SIMPLEX,1.1,(40,70,180),2)
  ok,enc=cv2.imencode(".jpg",img,[cv2.IMWRITE_JPEG_QUALITY,88])
  if not ok: raise HTTPException(500,"Image encoding failed")
  data=enc.tobytes()
 else:
  try:
   async with httpx.AsyncClient(timeout=10) as c:
    r=await c.get(f"{ESP32}/capture"); r.raise_for_status(); data=r.content
  except Exception as exc: raise HTTPException(502,f"Camera capture failed: {type(exc).__name__}")
 path=CAPTURE_DIR/f"{cid}.jpg"; path.write_bytes(data)
 captures[cid]={"path":path,"created_at":datetime.now(timezone.utc).isoformat(),"simulation":SIMULATION}
 return {"captureId":cid,"status":"captured","previewPath":f"/v1/captures/{cid}/image","simulation":SIMULATION}
@app.get("/v1/captures/{capture_id}/image")
def preview(capture_id:str):
 item=captures.get(capture_id)
 if not item or not item["path"].exists(): raise HTTPException(404,"Capture not found")
 return Response(item["path"].read_bytes(),media_type="image/jpeg",headers={"Cache-Control":"no-store"})
@app.post("/v1/captures/{capture_id}/analyze")
def analyze(capture_id:str):
 item=captures.get(capture_id)
 if not item: raise HTTPException(404,"Capture not found")
 image=cv2.imread(str(item["path"]))
 if image is None: raise HTTPException(422,"Invalid image")
 gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY); blur=float(cv2.Laplacian(gray,cv2.CV_64F).var()); brightness=float(gray.mean()/255)
 qc="review_required" if blur<35 or brightness<.20 or brightness>.95 else "pass"
 return {"captureId":capture_id,"quality":{"status":qc,"brightness":round(brightness,4),"blurScore":round(blur,2)},"analysis":{"pattern":"uncertain","confidence":None,"algorithmVersion":"0.1.0-qc-only"},"requiresAtlmReview":True,"simulation":item["simulation"]}
@app.delete("/v1/captures/{capture_id}")
def delete_capture(capture_id:str):
 item=captures.pop(capture_id,None)
 if item and item["path"].exists(): item["path"].unlink()
 return {"deleted":bool(item)}