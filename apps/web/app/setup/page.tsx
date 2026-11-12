"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import {
  Activity, ArrowLeft, CheckCircle2, CircleAlert, KeyRound,
  LoaderCircle, LockKeyhole, ShieldCheck,
} from "lucide-react";

type SetupStatus = { configured: boolean };
type SetupResponse = {
  ok: boolean;
  message: string;
  accounts?: string[];
  nextStep?: string;
};

export default function SetupPage() {
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [token, setToken] = useState("");
  const [passwords, setPasswords] = useState({ inuu: "", inu: "", lab: "" });
  const [confirmations, setConfirmations] = useState({ inuu: "", inu: "", lab: "" });
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<SetupResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    fetch("/api/setup/status", { cache: "no-store" })
      .then((response) => response.json())
      .then((data: SetupStatus) => { if (alive) setStatus(data); })
      .catch(() => { if (alive) setStatus({ configured: false }); });
    return () => { alive = false; };
  }, []);

  function updatePassword(id: "inuu" | "inu" | "lab", value: string) {
    setPasswords((current) => ({ ...current, [id]: value }));
    setResult(null);
    setError("");
  }

  function updateConfirmation(id: "inuu" | "inu" | "lab", value: string) {
    setConfirmations((current) => ({ ...current, [id]: value }));
    setResult(null);
    setError("");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setResult(null);

    for (const id of ["inuu", "inu", "lab"] as const) {
      if (passwords[id].length < 12) {
        setError("Semua password minimal 12 karakter.");
        return;
      }
      if (passwords[id] !== confirmations[id]) {
        setError("Konfirmasi password untuk ID " + id + " belum cocok.");
        return;
      }
    }
    if (new Set(Object.values(passwords)).size !== 3) {
      setError("Gunakan tiga password yang berbeda.");
      return;
    }

    setBusy(true);
    try {
      const response = await fetch("/api/setup/bootstrap", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, passwords }),
      });
      const data = (await response.json()) as SetupResponse;
      if (!response.ok) {
        setError(data.message || "Setup gagal. Periksa konfigurasi dan coba lagi.");
      } else {
        setResult(data);
        setToken("");
        setPasswords({ inuu: "", inu: "", lab: "" });
        setConfirmations({ inuu: "", inu: "", lab: "" });
      }
    } catch {
      setError("Tidak dapat menghubungi server setup. Coba periksa koneksi.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="setupShell">
      <section className="setupHero">
        <div className="setupBrand">
          <span className="setupBrandIcon"><Activity size={22}/></span>
          <span><b>WIDAL-SCAN AI</b><small>WIRELESS EDITION</small></span>
        </div>
        <div className="setupHeroContent">
          <span className="setupKicker">FIRST-TIME CONFIGURATION</span>
          <h1>Siapkan akses<br/><em>laboratorium.</em></h1>
          <p>Buat tiga akun awal dengan pembagian hak akses yang sudah ditentukan. Proses pembuatan akun dilakukan di server, bukan menyimpan password di browser atau repository.</p>
          <div className="setupTrust"><ShieldCheck size={18}/> Supabase Auth · Server-side setup · No default passwords</div>
        </div>
        <div className="setupHeroFoot">ALL SYSTEM PROVIDE BY INUU</div>
      </section>

      <section className="setupMain">
        <div className="setupTop"><Link href="/" className="backLink"><ArrowLeft size={16}/> Kembali ke login</Link><span className="setupStep">SETUP 01 / 01</span></div>
        <div className="setupCard">
          <div className="setupIcon"><KeyRound size={22}/></div>
          <span className="eyebrow">ACCOUNT INITIALIZATION</span>
          <h2>Konfigurasi akun awal</h2>
          <p className="setupLead">Sebelum mulai, jalankan migration Supabase 001, 002, dan 003 serta tambahkan environment variables di Vercel.</p>

          {status === null ? (
            <div className="setupStatus"><LoaderCircle size={17}/> Memeriksa konfigurasi server…</div>
          ) : status.configured ? (
            <div className="setupStatus ready"><CheckCircle2 size={17}/> Environment server tersedia. Lanjutkan pengisian password.</div>
          ) : (
            <div className="setupMissing">
              <CircleAlert size={18}/>
              <div><b>Konfigurasi server belum lengkap</b><p>Tambahkan tiga variable berikut di Vercel → Project → Settings → Environment Variables, pilih Production dan Preview, lalu redeploy.</p>
              <code>NEXT_PUBLIC_SUPABASE_URL</code><code>NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY</code><code>SUPABASE_SERVICE_ROLE_KEY</code><code>BOOTSTRAP_SETUP_TOKEN</code>
              <small>Setup token harus berupa string acak minimal 32 karakter. Service-role key hanya disimpan di server, tidak di browser.</small>
              </div>
            </div>
          )}

          <form onSubmit={submit} className="setupForm">
            <label className="setupLabel">One-time setup token
              <input value={token} onChange={(event) => setToken(event.target.value)} type={visible ? "text" : "password"} autoComplete="off" placeholder="Masukkan BOOTSTRAP_SETUP_TOKEN" required/>
            </label>
            <div className="setupFormDivider"><span>AKUN DAN ROLE</span></div>
            {([
              ["inuu", "Inuu", "Super Admin"],
              ["inu", "Inu", "Super Admin"],
              ["lab", "Laboratorium", "Lab User"],
            ] as const).map(([id, name, role]) => (
              <div className="setupAccount" key={id}>
                <div className="setupAccountHead"><span className="setupAvatar">{name.slice(0,1)}</span><span><b>{name}</b><small>ID: <strong>{id}</strong></small></span><em>{role}</em></div>
                <label className="setupLabel">Password baru
                  <input value={passwords[id]} onChange={(event) => updatePassword(id, event.target.value)} type={visible ? "text" : "password"} autoComplete="new-password" minLength={12} maxLength={128} placeholder="Minimal 12 karakter" required/>
                </label>
                <label className="setupLabel">Konfirmasi password
                  <input value={confirmations[id]} onChange={(event) => updateConfirmation(id, event.target.value)} type={visible ? "text" : "password"} autoComplete="new-password" minLength={12} maxLength={128} placeholder="Ulangi password" required/>
                </label>
              </div>
            ))}
            <label className="setupShow"><input type="checkbox" checked={visible} onChange={(event) => setVisible(event.target.checked)}/> Tampilkan password saat mengetik</label>
            {error && <div className="setupAlert"><CircleAlert size={17}/>{error}</div>}
            {result?.ok && <div className="setupSuccess"><CheckCircle2 size={18}/><div><b>Akun berhasil dibuat</b><p>{result.message}</p><Link href="/">Kembali ke halaman login →</Link></div></div>}
            <button className="setupSubmit" type="submit" disabled={busy || !status?.configured}>
              {busy ? <><LoaderCircle size={17} className="spin"/> Menyiapkan akun…</> : <><LockKeyhole size={17}/> Buat 3 akun dan aktifkan login</>}
            </button>
          </form>
          <div className="setupFootnote"><ShieldCheck size={15}/> Password tidak ditampilkan kembali, tidak dicatat ke log aplikasi, dan tidak masuk ke GitHub.</div>
        </div>
        <div className="setupPageFooter">WIDAL-SCAN AI · ALL SYSTEM PROVIDE BY INUU</div>
      </section>
    </main>
  );
}
