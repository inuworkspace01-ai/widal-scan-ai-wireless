"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import {
  Activity, ArrowLeft, CheckCircle2, CircleAlert, KeyRound,
  ExternalLink, LoaderCircle, LockKeyhole, RefreshCw, ShieldCheck,
} from "lucide-react";

type SetupStatus = {
  configured: boolean;
  missing: string[];
  presence: Record<string, boolean>;
};

const REQUIRED_ENV = [
  {
    key: "NEXT_PUBLIC_SUPABASE_URL",
    description: "Alamat project Supabase untuk koneksi aplikasi.",
  },
  {
    key: "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
    description: "Kunci publik untuk login dari browser.",
  },
  {
    key: "SUPABASE_SECRET_KEY",
    description: "Kunci rahasia server untuk membuat akun awal.",
  },
  {
    key: "BOOTSTRAP_SETUP_TOKEN",
    description: "Token acak minimal 32 karakter untuk mengunci proses setup.",
  },
] as const;
type SetupResponse = {
  ok: boolean;
  message: string;
  accounts?: string[];
  nextStep?: string;
};

export default function SetupPage() {
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [checkingStatus, setCheckingStatus] = useState(false);
  const [token, setToken] = useState("");
  const ACCOUNT_IDS = ["inuu", "avi_lab", "riska_lab"] as const;
  type AccountId = (typeof ACCOUNT_IDS)[number];
  const [passwords, setPasswords] = useState<Record<AccountId, string>>({ inuu: "", avi_lab: "", riska_lab: "" });
  const [confirmations, setConfirmations] = useState<Record<AccountId, string>>({ inuu: "", avi_lab: "", riska_lab: "" });
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<SetupResponse | null>(null);
  const [error, setError] = useState("");

  async function refreshSetupStatus() {
    setCheckingStatus(true);
    try {
      const response = await fetch("/api/setup/status", {
        cache: "no-store",
        headers: { "Cache-Control": "no-cache" },
      });
      if (!response.ok) throw new Error("Status endpoint unavailable");
      const data = (await response.json()) as SetupStatus;
      setStatus(data);
    } catch {
      setStatus({
        configured: false,
        missing: REQUIRED_ENV.map((item) => item.key),
        presence: {},
      });
    } finally {
      setCheckingStatus(false);
    }
  }

  useEffect(() => {
    void refreshSetupStatus();
  }, []);

  function updatePassword(id: AccountId, value: string) {
    setPasswords((current) => ({ ...current, [id]: value }));
    setResult(null);
    setError("");
  }

  function updateConfirmation(id: AccountId, value: string) {
    setConfirmations((current) => ({ ...current, [id]: value }));
    setResult(null);
    setError("");
  }

  function generatePassword(id: AccountId) {
    const bytes = new Uint8Array(20);
    window.crypto.getRandomValues(bytes);
    const generated = Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("");
    setPasswords((current) => ({ ...current, [id]: generated }));
    setConfirmations((current) => ({ ...current, [id]: generated }));
    setVisible(true);
    setResult(null);
    setError("");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setResult(null);

    for (const id of ACCOUNT_IDS) {
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
        setPasswords({ inuu: "", avi_lab: "", riska_lab: "" });
        setConfirmations({ inuu: "", avi_lab: "", riska_lab: "" });
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
          <p className="setupLead">Sebelum mulai, jalankan migration Supabase 001–004 dan tambahkan environment variables di Vercel.</p>

          <section className="setupConfigPanel" aria-live="polite">
            <div className="setupConfigHeader">
              <div>
                <b>Prasyarat koneksi Supabase & Vercel</b>
                <p>Nilai rahasia tidak pernah ditampilkan di halaman ini. Yang diperiksa hanya apakah variable sudah tersedia di server.</p>
              </div>
              {status && (
                <span className={status.configured ? "setupConfigBadge ready" : "setupConfigBadge missing"}>
                  {status.configured ? "LENGKAP" : `${status.missing.length} BELUM ADA`}
                </span>
              )}
            </div>

            {status === null ? (
              <div className="setupStatus"><LoaderCircle size={17}/> Memeriksa konfigurasi server…</div>
            ) : (
              <div className="setupEnvList">
                {REQUIRED_ENV.map((item) => {
                  const present = Boolean(status.presence?.[item.key]);
                  return (
                    <div className="setupEnvRow" key={item.key}>
                      <div className="setupEnvCopy">
                        <code>{item.key}</code>
                        <small>{item.description}</small>
                      </div>
                      <span className={present ? "setupEnvState ready" : "setupEnvState missing"}>
                        {present ? "TERPASANG" : "BELUM ADA"}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}

            {status?.configured ? (
              <div className="setupStatus ready"><CheckCircle2 size={17}/> Semua variable tersedia. Kamu sudah bisa menyiapkan password akun.</div>
            ) : (
              <div className="setupConfigHelp">
                <b>Langkah konfigurasi</b>
                <ol>
                  <li>Buka project <strong>widal-scan-ai-wireless</strong> di Vercel.</li>
                  <li>Masuk ke <strong>Settings → Environment Variables</strong>.</li>
                  <li>Tambahkan variable yang berstatus <strong>BELUM ADA</strong> di atas.</li>
                  <li>Pilih <strong>Production</strong> dan <strong>Preview</strong>, simpan, lalu redeploy.</li>
                  <li>Kembali ke halaman ini dan tekan <strong>Periksa ulang</strong>.</li>
                </ol>
                <a href="https://vercel.com/inuworkspace01-3852/widal-scan-ai-wireless/settings/environment-variables" target="_blank" rel="noreferrer">
                  Buka Environment Variables Vercel <ExternalLink size={13}/>
                </a>
                <p><strong>Catatan:</strong> menghubungkan Supabase sebagai integrasi tidak selalu memasukkan key ke Environment Variables project Vercel. Pastikan empat variable ini benar-benar ditambahkan pada project yang menjalankan website.</p>
              </div>
            )}

            <button type="button" className="setupRefresh" onClick={() => void refreshSetupStatus()} disabled={checkingStatus}>
              {checkingStatus ? <><LoaderCircle size={15} className="spin"/> Memeriksa…</> : <><RefreshCw size={15}/> Periksa ulang konfigurasi</>}
            </button>
          </section>

          {status?.configured ? (
          <form onSubmit={submit} className="setupForm">
            <label className="setupLabel">One-time setup token
              <input value={token} onChange={(event) => setToken(event.target.value)} type={visible ? "text" : "password"} autoComplete="off" placeholder="Masukkan token setup yang sama dengan BOOTSTRAP_SETUP_TOKEN di Vercel" required/>
            </label>
            <div className="setupFormDivider"><span>AKUN DAN ROLE</span></div>
            {([
              ["inuu", "Inuu", "Super Admin"],
              ["avi_lab", "Avi_Lab", "Lab User"],
              ["riska_lab", "Riska_lab", "Lab User"],
            ] as const).map(([id, name, role]) => (
              <div className="setupAccount" key={id}>
                <div className="setupAccountHead"><span className="setupAvatar">{name.slice(0,1)}</span><span><b>{name}</b><small>ID login: <strong>{name}</strong></small></span><em>{role}</em><button type="button" className="generatePassword" onClick={() => generatePassword(id)}>Generate password</button></div>
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
            <div className="setupReminder">Gunakan tombol Generate password untuk membuat password acak yang kuat. Simpan ketiganya di password manager sebelum menekan tombol. Password tidak ditampilkan kembali setelah akun berhasil dibuat.</div>
            <button className="setupSubmit" type="submit" disabled={busy || !status?.configured}>
              {busy ? <><LoaderCircle size={17} className="spin"/> Menyiapkan akun…</> : <><LockKeyhole size={17}/> Buat 3 akun dan aktifkan login</>}
            </button>
          </form>
          ) : (
            <div className="setupFormDisabled">
              <LockKeyhole size={18}/>
              <div><b>Form pembuatan akun dikunci sementara</b><p>Kolom token dan password akan muncul setelah seluruh konfigurasi server terpasang. Ini mencegah token dimasukkan ketika endpoint belum siap.</p></div>
            </div>
          )}
          <div className="setupFootnote"><ShieldCheck size={15}/> Password tidak ditampilkan kembali, tidak dicatat ke log aplikasi, dan tidak masuk ke GitHub.</div>
        </div>
        <div className="setupPageFooter">WIDAL-SCAN AI · ALL SYSTEM PROVIDE BY INUU</div>
      </section>
    </main>
  );
}
