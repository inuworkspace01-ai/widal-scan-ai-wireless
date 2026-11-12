"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import {
  Activity, Camera, Wifi, WifiOff, Settings, Image as ImageIcon,
  ShieldCheck, RefreshCw, LogOut, BrainCircuit, Database, Users,
  BookOpen, LockKeyhole, ArrowUpRight, FlaskConical, Info,
} from "lucide-react";
import { getSupabaseBrowserClient } from "../lib/supabase/client";

const BRIDGE = "http://127.0.0.1:8765";

type Profile = {
  username: string;
  display_name: string;
  role: "admin" | "atlm";
  is_active: boolean;
};
type Status = {
  ok?: boolean;
  simulation?: boolean;
  device?: { connected?: boolean; ip?: string; name?: string };
};
type Capture = {
  captureId: string;
  status: string;
  previewPath?: string;
  simulation?: boolean;
};

const SOURCES = [
  {
    title: "Typhoid Dataset — Kaggle",
    kind: "Candidate dataset · tabular",
    status: "Needs verification",
    description: "A 2026 paper links to this exact Kaggle listing and describes 31,087 anonymised records, 21 variables and four classes. Verify the CSV schema, label quality, provenance and licence before use.",
    url: "https://www.kaggle.com/datasets/rajmohnani12/typhoid-dataset",
    note: "For exploratory clinical-feature research only; not image labels."
  },
  {
    title: "WHO Laboratory Manual for Typhoid and Paratyphoid",
    kind: "Guideline reference · 2026",
    status: "Reference only",
    description: "Laboratory methods and context for enteric fever. The publication page lists CC BY-NC-SA 3.0 IGO; attribution and non-commercial/share-alike terms apply.",
    url: "https://www.who.int/publications/b/65402",
    note: "A guideline is not a labelled training dataset."
  },
  {
    title: "Kemenkes RI — PNPK Demam Tifoid Dewasa",
    kind: "Clinical governance · 2026",
    status: "Reference only",
    description: "Kepmenkes No. HK.01.07/MENKES/875/2026. Used for Indonesian clinical-context and SOP review, not as generated patient training rows.",
    url: "https://jdih.kemkes.go.id/storage/documents/pdfs/2026kepmenkes875.pdf",
    note: "Adult guideline; local SOP and professional review remain necessary."
  },
  {
    title: "CDC — Clinical Guidance for Typhoid Fever",
    kind: "Diagnostic limitation reference",
    status: "Safety reference",
    description: "CDC describes blood culture as the mainstay and does not recommend Widal serology because of false positives.",
    url: "https://www.cdc.gov/typhoid-fever/hcp/clinical-guidance/",
    note: "Visual image grading must never be shown as a typhoid diagnosis."
  }
];

export default function Home() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [supabaseReady, setSupabaseReady] = useState(false);
  const [loginId, setLoginId] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [authError, setAuthError] = useState("");
  const [signingIn, setSigningIn] = useState(false);
  const [tab, setTab] = useState("overview");
  const [bridge, setBridge] = useState<Status | null>(null);
  const [busy, setBusy] = useState(false);
  const [capture, setCapture] = useState<Capture | null>(null);
  const [preview, setPreview] = useState("");
  const [message, setMessage] = useState("Bridge belum diperiksa.");

  useEffect(() => {
    const supabase = getSupabaseBrowserClient();
    setSupabaseReady(Boolean(supabase));
    if (!supabase) {
      setAuthLoading(false);
      return;
    }

    const client = supabase;
    let active = true;
    async function restoreSession() {
      const { data, error } = await client.auth.getSession();
      if (!active) return;
      if (error) setAuthError("Sesi tidak dapat dibaca. Silakan login kembali.");
      if (data.session?.user) {
        const { data: row, error: profileError } = await client
          .from("profiles")
          .select("username,display_name,role,is_active")
          .eq("user_id", data.session.user.id)
          .single();

        if (!active) return;
        if (profileError || !row || !row.is_active || !["admin", "atlm"].includes(row.role)) {
          await client.auth.signOut();
          setAuthError("Akun tidak aktif atau belum memiliki role aplikasi.");
        } else {
          setProfile(row as Profile);
        }
      }
      setAuthLoading(false);
    }
    void restoreSession();
    return () => { active = false; };
  }, []);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthError("");
    const username = loginId.trim().toLowerCase();
    if (!["inuu", "avi_lab", "riska_lab"].includes(username)) {
      setAuthError("ID yang terdaftar: Inuu, Avi_Lab, atau Riska_lab.");
      return;
    }
    if (!loginPassword) {
      setAuthError("Masukkan password akun.");
      return;
    }
    const supabase = getSupabaseBrowserClient();
    if (!supabase) {
      setAuthError("Supabase belum dikonfigurasi. Isi environment variable dan jalankan migration.");
      return;
    }

    setSigningIn(true);
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email: username + "@login.widal-scan.invalid",
        password: loginPassword,
      });
      if (error || !data.user) {
        setAuthError("Login gagal. Periksa ID dan password.");
        return;
      }

      const { data: row, error: profileError } = await supabase
        .from("profiles")
        .select("username,display_name,role,is_active")
        .eq("user_id", data.user.id)
        .single();

      if (profileError || !row || !row.is_active || !["admin", "atlm"].includes(row.role)) {
        await supabase.auth.signOut();
        setAuthError("Profil akun belum disiapkan atau akses dinonaktifkan.");
        return;
      }

      setProfile(row as Profile);
      setLoginPassword("");
      setTab("overview");
    } catch {
      setAuthError("Tidak dapat menghubungi layanan autentikasi.");
    } finally {
      setSigningIn(false);
    }
  }

  async function handleLogout() {
    const supabase = getSupabaseBrowserClient();
    if (supabase) await supabase.auth.signOut();
    setProfile(null);
    setBridge(null);
    setPreview("");
    setCapture(null);
    setTab("overview");
  }

  async function checkBridge() {
    try {
      const response = await fetch(BRIDGE + "/v1/health", { cache: "no-store" });
      if (!response.ok) throw new Error("Bridge tidak merespons");
      const data = await response.json();
      setBridge(data);
      setMessage("Windows Bridge terhubung.");
    } catch {
      setBridge(null);
      setMessage("Bridge belum aktif. Jalankan FastAPI pada Windows PC.");
    }
  }

  useEffect(() => {
    if (profile) void checkBridge();
  }, [profile]);

  async function takePicture() {
    setBusy(true);
    setMessage("Meminta kamera mengambil gambar...");
    try {
      const response = await fetch(BRIDGE + "/v1/capture", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile: "widal-slide-v1" }),
      });
      if (!response.ok) throw new Error("Gagal mengambil gambar dari Bridge.");
      const data: Capture = await response.json();
      setCapture(data);
      const imageResponse = await fetch(BRIDGE + data.previewPath);
      if (!imageResponse.ok) throw new Error("Preview tidak tersedia.");
      const blob = await imageResponse.blob();
      setPreview(URL.createObjectURL(blob));
      setMessage(data.simulation ? "Preview simulasi. Ini bukan foto spesimen." : "Foto berhasil diambil.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Terjadi kesalahan.");
    } finally {
      setBusy(false);
    }
  }

  const isAdmin = profile?.role === "admin";
  const nav = [
    { id: "overview", label: "Overview", icon: Activity },
    { id: "capture", label: "Capture", icon: Camera },
    ...(isAdmin ? [
      { id: "device", label: "Device & Wi-Fi", icon: Wifi },
      { id: "models", label: "AI / Machine Learning", icon: BrainCircuit },
      { id: "datasets", label: "Dataset & References", icon: Database },
      { id: "accounts", label: "Account Access", icon: Users },
      { id: "settings", label: "Settings", icon: Settings },
    ] : []),
    { id: "history", label: "History", icon: ImageIcon },
  ];
  const pageTitle = nav.find((item) => item.id === tab)?.label || "Overview";

  if (authLoading) {
    return <main className="authLoading"><div className="brandIcon"><Activity size={22}/></div><b>Memeriksa sesi WIDAL-SCAN AI...</b></main>;
  }

  if (!profile) {
    return (
      <main className="loginShell">
        <section className="loginIntro">
          <div className="loginBrand"><div className="brandIcon"><Activity size={25}/></div><span>ALL SYSTEM PROVIDE BY <b>INUU</b></span></div>
          <div className="loginEyebrow">WIRELESS LABORATORY PLATFORM</div>
          <h1>WIDAL-SCAN <em>AI</em></h1>
          <div className="loginEdition">WIRELESS EDITION <Wifi size={15}/></div>
          <p className="loginLead">Satu workspace untuk dokumentasi citra, pembacaan visual berbantuan AI, serta pengelolaan perangkat laboratorium.</p>
          <div className="loginFeatureGrid">
            <div><Camera size={19}/><b>Image Capture</b><small>ESP32-CAM wireless</small></div>
            <div><BrainCircuit size={19}/><b>AI Research</b><small>Computer vision</small></div>
            <div><ShieldCheck size={19}/><b>Role Access</b><small>Super admin & lab</small></div>
            <div><Wifi size={19}/><b>Local Bridge</b><small>Windows PC connection</small></div>
          </div>
          <div className="loginCopyright">SMART LAB · COMPUTER VISION · IoT</div>
        </section>
        <section className="loginPanelWrap">
          <div className="loginPanel">
            <div className="loginLock"><LockKeyhole size={22}/></div>
            <span className="eyebrow">SECURE ACCOUNT</span>
            <h2>Masuk ke dashboard</h2>
            <p className="loginSubtitle">Gunakan ID akun yang sudah didaftarkan oleh administrator.</p>
            <form onSubmit={handleLogin} className="loginForm">
              <label>ID Pengguna
                <input value={loginId} onChange={(event) => setLoginId(event.target.value)} placeholder="Contoh: Avi_Lab" autoComplete="username" required/>
              </label>
              <label>Password
                <div className="passwordField">
                  <input value={loginPassword} onChange={(event) => setLoginPassword(event.target.value)} type={showPassword ? "text" : "password"} placeholder="Masukkan password" autoComplete="current-password" required/>
                  <button type="button" className="showPassword" onClick={() => setShowPassword(!showPassword)}>{showPassword ? "Sembunyikan" : "Lihat"}</button>
                </div>
              </label>
              {authError && <div className="authError" role="alert">{authError}</div>}
              {!supabaseReady && <div className="authSetupNotice"><Info size={16}/> Login belum aktif: konfigurasi Supabase dan akun bootstrap belum dijalankan.</div>}
              <button className="loginSubmit" type="submit" disabled={signingIn || !supabaseReady}>{signingIn ? "Memverifikasi..." : "Masuk Dashboard"}</button>
            </form>
            <div className="accountHints">
              <span>AKUN YANG DISIAPKAN</span>
              <div><code>Inuu</code><small>Super Admin</small><code>Avi_Lab</code><small>Lab User</small><code>Riska_lab</code><small>Lab User</small></div>
            </div>
            <Link href="/setup" className="firstSetupLink">Pertama kali menggunakan aplikasi? <b>Siapkan akun awal <ArrowUpRight size={13}/></b></Link>
            <div className="loginFooter">WIDAL-SCAN AI · ALL SYSTEM PROVIDE BY INUU</div>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand"><div className="brandIcon"><Activity size={22}/></div><div><b>WIDAL-SCAN AI</b><small>WIRELESS EDITION</small></div></div>
        <div className="navLabel">WORKSPACE</div>
        {nav.map((item) => {
          const Icon = item.icon;
          return <button key={item.id} className={"navItem " + (tab === item.id ? "active" : "")} onClick={() => setTab(item.id)}><Icon size={18}/>{item.label}</button>;
        })}
        <div className="sideBottom"><i/> Prototype Environment <small>v0.2.0 · ALL SYSTEM PROVIDE BY INUU</small></div>
      </aside>

      <section className="main">
        <header className="topbar">
          <div><span className="eyebrow">LABORATORY INTELLIGENCE PLATFORM</span><h1>{pageTitle}</h1></div>
          <div className="userMenu"><div className="userAvatar">{profile.display_name.slice(0, 1).toUpperCase()}</div><div className="userText"><b>{profile.display_name}</b><small>{isAdmin ? "SUPER ADMIN" : "LAB USER"}</small></div><button className="logoutBtn" onClick={() => void handleLogout()} title="Keluar"><LogOut size={17}/></button></div>
        </header>

        <div className="content">
          {tab === "overview" && <>
            <div className="welcome">
              <div><span className="eyebrow light">SMART LABORATORY · COMPUTER VISION · IoT</span><h2>Widal imaging workspace.</h2><p>Selamat datang, {profile.display_name}. Kelola koneksi perangkat, dokumentasikan citra, dan tinjau status riset AI dalam satu tempat.</p></div>
              <div className="heroMark"><Camera size={48}/><span>WIRELESS</span></div>
            </div>
            <div className="stats">
              <div className="stat"><span>BRIDGE STATUS</span><b>{bridge?.ok ? "Connected" : "Offline"}</b><small>{bridge?.simulation ? "Simulation mode" : "Windows local service"}</small></div>
              <div className="stat"><span>DEVICE STATUS</span><b>{bridge?.device?.connected ? "Connected" : "Not detected"}</b><small>{bridge?.device?.ip || "Waiting for ESP32-CAM"}</small></div>
              <div className="stat"><span>AI MODEL STATUS</span><b>Research setup</b><small>Belum ada model tervalidasi</small></div>
            </div>
            <div className="grid2">
              <div className="panel">
                <div className="panelHead"><div><h3>Device connection</h3><p>Local network connection</p></div><button className="iconBtn" onClick={() => void checkBridge()}><RefreshCw size={16}/></button></div>
                <div className="connection"><div className="connectionIcon">{bridge?.ok ? <Wifi size={23}/> : <WifiOff size={23}/>}</div><div><b>{bridge?.ok ? "Bridge available" : "Bridge unavailable"}</b><small>{message}</small></div></div>
                {isAdmin && <button className="primary" onClick={() => setTab("device")}>Device settings</button>}
                {!isAdmin && <button className="primary" onClick={() => setTab("capture")}>Open capture workspace</button>}
              </div>
              <div className="panel"><h3>AI training status</h3><div className="modelStatus"><BrainCircuit size={27}/><div><b>Visual grade model</b><small>Pipeline tersedia · menunggu data citra ATLM</small></div><span className="statusTag pending">NOT TRAINED</span></div><div className="modelStatus"><Database size={27}/><div><b>Clinical tabular baseline</b><small>Dataset kandidat · perlu pemeriksaan lisensi dan label</small></div><span className="statusTag research">RESEARCH</span></div>{isAdmin && <button className="secondary fullButton" onClick={() => setTab("models")}>Open AI workspace</button>}</div>
            </div>
          </>}

          {tab === "capture" && <div className="grid2 captureLayout">
            <div className="panel"><h3>Camera preview</h3><div className="preview">{preview ? <img src={preview} alt="Captured preview"/> : <div><Camera size={42}/><b>Camera preview</b><span>Tekan Take Picture untuk meminta gambar dari Windows Bridge.</span></div>}</div><div className="actions"><button className="primary" disabled={busy} onClick={() => void takePicture()}>{busy ? "Processing..." : "Take Picture"}</button><button className="secondary" onClick={() => {setPreview("");setCapture(null);}}>Clear preview</button></div>{capture?.simulation && <div className="notice">SIMULATION IMAGE — bukan citra pemeriksaan Widal.</div>}</div>
            <div className="panel"><h3>Capture information</h3><div className="infoRow"><span>Capture ID</span><b>{capture?.captureId || "—"}</b></div><div className="infoRow"><span>Status</span><b>{capture?.status || "Waiting"}</b></div><div className="infoRow"><span>Bridge</span><b>{bridge?.ok ? "Online" : "Offline"}</b></div><p>{message}</p><div className="notice">Hasil pembacaan visual bersifat eksperimental dan wajib diverifikasi ATLM. Aplikasi ini bukan alat diagnosis demam tifoid.</div></div>
          </div>}

          {tab === "device" && isAdmin && <div className="panel formPanel"><h3>Wireless device connection</h3><p>PC Windows dan ESP32-CAM harus berada pada jaringan Wi-Fi lokal 2,4 GHz yang sama.</p><div className="infoRow"><span>Bridge endpoint</span><b>http://127.0.0.1:8765</b></div><div className="infoRow"><span>Current device</span><b>{bridge?.device?.ip || "192.168.50.20 (placeholder)"}</b></div><div className="infoRow"><span>Connection status</span><b>{bridge?.ok ? "Bridge online" : "Bridge offline"}</b></div><div className="notice">Firmware provisioning Wi-Fi yang aman belum diimplementasikan. Jangan mengirim atau menyimpan password Wi-Fi di dashboard sampai mekanisme pairing dan autentikasi perangkat selesai.</div><button className="primary" onClick={() => void checkBridge()}>Check local bridge <RefreshCw size={15}/></button></div>}

          {tab === "models" && isAdmin && <div className="stack">
            <div className="sectionIntro"><div><span className="eyebrow">AI RESEARCH WORKSPACE</span><h2>Model & training pipeline</h2><p>Dua tugas ML dipisahkan agar model pembacaan citra tidak tercampur dengan model riset data klinis.</p></div><span className="statusTag pending">NO VALIDATED MODEL</span></div>
            <div className="grid2">
              <div className="panel modelCard"><div className="largeIcon"><Camera size={24}/></div><span className="eyebrow">COMPUTER VISION</span><h3>Widal visual-grade classifier</h3><p>ResNet-18 research starter untuk memprediksi grade visual per-well: 0, 1+, 2+, 3+, 4+.</p><div className="modelMeta"><span>Architecture</span><b>ResNet-18</b></div><div className="modelMeta"><span>Dataset</span><b>Foto Widal berlabel ATLM</b></div><div className="modelMeta"><span>Current status</span><b>Pipeline only · not trained</b></div><div className="notice">Butuh citra spesimen asli, label ATLM, SOP dan pembagian data per spesimen. Kaggle tabular tidak dapat menggantikan gambar Widal.</div></div>
              <div className="panel modelCard"><div className="largeIcon"><FlaskConical size={24}/></div><span className="eyebrow">TABULAR ML</span><h3>Clinical research baseline</h3><p>Random Forest baseline untuk eksplorasi dataset klinis setelah kolom, label, provenance, dan lisensinya diverifikasi.</p><div className="modelMeta"><span>Architecture</span><b>Random Forest + preprocessing</b></div><div className="modelMeta"><span>Dataset candidate</span><b>Kaggle Typhoid Dataset</b></div><div className="modelMeta"><span>Current status</span><b>Runner ready · data not imported</b></div><div className="notice">Keluaran hanya riset eksploratif; bukan prediksi diagnosis individual atau rekomendasi terapi.</div></div>
            </div>
            <div className="panel"><h3>Training workflow</h3><div className="workflow"><div><span>01</span><b>Collect & verify</b><small>Data provenance, licence, SOP</small></div><div><span>02</span><b>Annotate</b><small>ATLM reference labels</small></div><div><span>03</span><b>Train</b><small>Group-aware split</small></div><div><span>04</span><b>Evaluate</b><small>Macro-F1, recall, confusion matrix</small></div><div><span>05</span><b>Review</b><small>ATLM + independent validation</small></div></div></div>
          </div>}

          {tab === "datasets" && isAdmin && <div className="stack">
            <div className="sectionIntro"><div><span className="eyebrow">DATA GOVERNANCE</span><h2>Dataset & reference library</h2><p>Sumber data dipilah antara kandidat data latih, pedoman laboratorium, dan referensi keselamatan.</p></div><span className="statusTag research">4 SOURCES</span></div>
            {SOURCES.map((source) => <div className="sourceCard" key={source.title}><div className="sourceIcon"><BookOpen size={21}/></div><div className="sourceBody"><div className="sourceHeading"><div><h3>{source.title}</h3><small>{source.kind}</small></div><span className="statusTag research">{source.status}</span></div><p>{source.description}</p><small className="sourceNote">{source.note}</small><a href={source.url} target="_blank" rel="noreferrer">Open source <ArrowUpRight size={14}/></a></div></div>)}
            <div className="notice"><b>Prinsip penting:</b> WHO/Kemenkes menyediakan pedoman, bukan label gambar. Dataset Kaggle tabular hanya kandidat setelah lisensi dan kualitas label diperiksa. Foto Widal untuk computer vision harus dikumpulkan dengan setup alat ini dan diberi label ATLM.</div>
          </div>}

          {tab === "accounts" && isAdmin && <div className="panel"><div className="sectionIntro"><div><span className="eyebrow">ACCESS CONTROL</span><h2>Account access</h2><p>Daftar ID awal dan hak akses yang diminta.</p></div><span className="statusTag success">ROLE MAPPED</span></div><div className="accountRow"><div className="userAvatar">I</div><div><b>Inuu</b><small>Super Admin · full dashboard access</small></div><span className="roleBadge admin">SUPER ADMIN</span></div><div className="accountRow"><div className="userAvatar">A</div><div><b>Avi_Lab</b><small>Lab User · capture and examination workspace</small></div><span className="roleBadge lab">LAB USER</span></div><div className="accountRow"><div className="userAvatar">R</div><div><b>Riska_lab</b><small>Lab User · capture and examination workspace</small></div><span className="roleBadge lab">LAB USER</span></div><div className="notice">Password tiap akun dibuat saat setup awal melalui wizard. Tidak ada password default di source code. Pengguna lab hanya dapat membaca dan mengubah pemeriksaan miliknya sendiri.</div></div>}

          {tab === "history" && <div className="panel"><h3>Examination history</h3><p>Riwayat tersimpan di Supabase setelah konfigurasi project dan tabel selesai. Saat ini belum ada data pemeriksaan.</p><div className="empty"><ImageIcon size={32}/><b>No examinations yet</b><small>Data demo tidak dihitung sebagai hasil pemeriksaan.</small></div></div>}

          {tab === "settings" && isAdmin && <div className="panel"><h3>System settings</h3><div className="infoRow"><span>Application</span><b>WIDAL-SCAN AI — Wireless Edition</b></div><div className="infoRow"><span>Signed in as</span><b>{profile.username}</b></div><div className="infoRow"><span>Access role</span><b>Super Admin</b></div><div className="infoRow"><span>AI engine</span><b>Windows · Python · OpenCV · PyTorch</b></div><div className="infoRow"><span>Cloud</span><b>Vercel + Supabase</b></div><div className="infoRow"><span>Attribution</span><b>ALL SYSTEM PROVIDE BY INUU</b></div></div>}

          <footer>ALL SYSTEM PROVIDE BY INUU <span>·</span> WIDAL-SCAN AI Wireless Edition</footer>
        </div>
      </section>
    </main>
  );
}
