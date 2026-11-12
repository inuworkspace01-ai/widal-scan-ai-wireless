#include <Arduino.h>
#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
// AI Thinker ESP32-CAM default pin map. Verify your exact board before flashing.
const char* WIFI_SSID = "YOUR_2G_WIFI";
const char* WIFI_PASSWORD = "CHANGE_ME";
WebServer server(80);
void handleStatus(){ server.send(200,"application/json","{\"ok\":true,\"device\":\"ESP32-CAM\"}"); }
void handleCapture(){
 camera_fb_t* fb=esp_camera_fb_get();
 if(!fb){server.send(503,"text/plain","camera capture failed");return;}
 server.sendHeader("Content-Disposition","inline; filename=capture.jpg");
 server.send_P(200,"image/jpeg",(const char*)fb->buf,fb->len);
 esp_camera_fb_return(fb);
}
void setup(){
 Serial.begin(115200);
 camera_config_t c={};
 c.ledc_channel=LEDC_CHANNEL_0;c.ledc_timer=LEDC_TIMER_0;
 c.pin_d0=5;c.pin_d1=18;c.pin_d2=19;c.pin_d3=21;c.pin_d4=36;c.pin_d5=39;c.pin_d6=34;c.pin_d7=35;
 c.pin_xclk=0;c.pin_pclk=22;c.pin_vsync=25;c.pin_href=23;c.pin_sccb_sda=26;c.pin_sccb_scl=27;c.pin_pwdn=32;c.pin_reset=-1;c.xclk_freq_hz=20000000;c.pixel_format=PIXFORMAT_JPEG;
 c.frame_size=FRAMESIZE_SVGA;c.jpeg_quality=12;c.fb_count=1;
 if(esp_camera_init(&c)!=ESP_OK){Serial.println("Camera init failed");return;}
 WiFi.begin(WIFI_SSID,WIFI_PASSWORD);
 while(WiFi.status()!=WL_CONNECTED){delay(500);Serial.print(".");}
 server.on("/status",HTTP_GET,handleStatus);server.on("/capture",HTTP_GET,handleCapture);server.begin();
}
void loop(){server.handleClient();}