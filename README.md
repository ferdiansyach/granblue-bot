# 🤖 Granblue Automation — v3.1.1

> Bot otomasi berbasis Python untuk game **Granblue Fantasy** (browser).  
> Menggunakan computer vision (OpenCV + EasyOCR) dan kontrol mouse/keyboard otomatis.

---

## ⚠️ Ketentuan Penggunaan (Terms of Use)

**Baca dan pahami ketentuan berikut sebelum menggunakan proyek ini:**

1. **Hanya untuk keperluan pribadi & edukasi.**  
   Proyek ini dibuat sebagai eksperimen otomasi dan pembelajaran. Tidak boleh digunakan untuk keuntungan komersial atau dijual dalam bentuk apapun.

2. **Risiko akun ditanggung pengguna sepenuhnya.**  
   Penggunaan bot pada game online dapat melanggar Terms of Service (ToS) dari Cygames. Segala konsekuensi seperti **ban, suspend, atau penghapusan akun** adalah tanggung jawab pengguna. Developer tidak bertanggung jawab atas kerugian apapun.

3. **Dilarang mendistribusikan ulang tanpa izin.**  
   Dilarang menyebarluaskan, menjual, atau mem-fork proyek ini tanpa izin eksplisit dari pemilik repositori.

4. **Tidak ada garansi.**  
   Software ini disediakan "as-is" tanpa garansi apapun. Developer tidak menjamin software akan berjalan sempurna di semua sistem atau kondisi.

5. **Jaga privasi & keamanan.**  
   Jangan pernah membagikan file `settings.json` kamu secara publik karena berisi token API (Twitter, Discord) yang bersifat rahasia.

6. **Gunakan secara bertanggung jawab.**  
   Hindari penggunaan yang dapat merugikan pemain lain (misalnya: flooding raid room, monopoli resource).

---

## 📋 Deskripsi Proyek

Granblue Automation adalah bot otomasi yang mampu menjalankan berbagai mode pertempuran di Granblue Fantasy secara otomatis menggunakan:

- **Computer Vision** — Deteksi elemen game lewat screenshot dengan OpenCV & template matching
- **OCR** — Pembacaan teks di layar menggunakan EasyOCR
- **Mouse & Keyboard Automation** — Kontrol otomatis via PyAutoGUI dengan gerakan mouse bezier curve
- **Multi-process** — Bot berjalan pada proses terpisah agar tidak memblokir UI
- **Notifikasi** — Integrasi Discord & Twitter untuk pemberitahuan real-time

---

## 🎮 Mode yang Didukung

| Mode | File |
|---|---|
| Quest (Normal/Hard/VH/EX) | `quest.py` |
| Raid | `raid.py` |
| Event | `event.py` |
| Guild Wars | `guild_wars.py` |
| Coop | `coop.py` |
| Arcarum | `arcarum.py` |
| Arcarum Sandbox | `arcarum_sandbox.py` |
| Dread Barrage | `dread_barrage.py` |
| Proving Grounds | `proving_grounds.py` |
| Rise of the Beasts (RotB) | `rotb.py` |
| Special | `special.py` |
| Generic | `generic.py` / `generic_v2.py` |

---

## 🛠️ Persyaratan Sistem

| Komponen | Kebutuhan |
|---|---|
| OS | Windows 10/11 (64-bit) |
| Python | 3.9+ |
| GPU | NVIDIA dengan CUDA 11.6 (untuk PyTorch) |
| RAM | Minimal 8 GB |
| Browser | Chrome/Edge dengan Granblue Fantasy aktif |
| Resolusi | Disesuaikan dengan pengaturan `customScale` |

---

## 📦 Instalasi & Setup

### 1. Clone repositori

```bash
git clone https://github.com/<username>/<repo-name>.git
cd <repo-name>
```

### 2. Buat virtual environment

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependensi

```bash
pip install -r requirements.txt
```

> **Catatan:** PyTorch (`torch`, `torchvision`, `torchaudio`) akan diunduh dari PyTorch server dan memerlukan koneksi internet stabil. Ukuran file cukup besar (~2 GB).

### 4. Konfigurasi `settings.json`

Edit file `backend/settings.json`. **Jangan commit file ini ke Git** (sudah dikecualikan via `.gitignore`).

Konfigurasi utama:

```json
{
  "game": {
    "farmingMode": "Raid",
    "item": "Tiamat Omega",
    "mission": "Lvl 100 Tiamat Omega Ayr",
    "itemAmount": 100,
    "groupNumber": 3,
    "partyNumber": 2
  }
}
```

### 5. Jalankan bot

```bash
cd backend
python main.py
```

Atau gunakan executable langsung:

```bash
"Granblue Automation.exe"
```

---

## ⚙️ Konfigurasi Lanjutan

### Combat Script

Buat file `.txt` di folder `scripts/` untuk mendefinisikan urutan aksi tempur. Contoh format (`full_auto.txt`):

```
Turn 1:
enableFullAuto
end
```

Lihat contoh script yang sudah tersedia di folder `scripts/` untuk referensi lebih lanjut.

### Notifikasi Discord

Aktifkan di `settings.json`:

```json
"discord": {
  "enableDiscordNotifications": true,
  "discordToken": "BOT_TOKEN_KAMU",
  "discordUserID": "USER_ID_KAMU"
}
```

### Notifikasi Twitter

```json
"twitter": {
  "twitterUseVersion2": true,
  "twitterAPIKey": "...",
  "twitterAPIKeySecret": "...",
  "twitterAccessToken": "...",
  "twitterAccessTokenSecret": "..."
}
```

---

## 📁 Struktur Proyek

```
Granblue.Automation.v3.1.1/
├── backend/
│   ├── bot/
│   │   ├── game.py              # Logic utama permainan
│   │   ├── combat_mode.py       # Mode pertempuran
│   │   ├── dom_clicker.py       # Kontrol DOM browser
│   │   ├── window.py            # Manajemen window
│   │   └── game_modes/          # Modul setiap mode farming
│   ├── model/                   # Model ML (jika ada)
│   ├── utils/                   # Utilitas (logging, image, dll)
│   ├── main.py                  # Entry point
│   ├── requirements.txt         # Daftar dependensi Python
│   └── settings.json            # Konfigurasi (JANGAN di-commit!)
├── images/                      # Template gambar untuk deteksi
├── scripts/                     # Script combat kustom (.txt)
├── logs/                        # Log session bot (diabaikan Git)
└── README.md                    # Dokumentasi ini
```

---

## 🐛 Debugging & Troubleshooting

- Aktifkan `"debugMode": true` di `settings.json` untuk log lebih detail.
- Log tersimpan di folder `logs/` dan dikecualikan dari Git.
- Jika bot tidak mendeteksi elemen dengan benar, coba sesuaikan:
  - `"confidence"` dan `"confidenceAll"` di bagian `device`
  - `"customScale"` sesuai resolusi monitor
  - Nilai `adjustment` untuk fine-tuning timing

---

## 🤝 Kontribusi

Pull request dipersilakan untuk:
- Perbaikan bug
- Penambahan mode farming baru
- Peningkatan akurasi deteksi

Pastikan kode yang di-submit:
1. Tidak mengandung token/secret apapun
2. Mengikuti gaya penulisan yang ada (docstring, type hint)
3. Disertai penjelasan perubahan di PR description

---

## 📄 Lisensi

Proyek ini **tidak memiliki lisensi open-source resmi**.  
Penggunaan terbatas untuk **keperluan pribadi dan edukasi** saja.  
Redistribusi dan penggunaan komersial **dilarang** tanpa izin tertulis dari pemilik.

---

## ⚡ Disclaimer

> Proyek ini **tidak berafiliasi, disponsori, atau didukung** oleh Cygames, Inc.  
> "Granblue Fantasy" adalah merek dagang milik Cygames, Inc.  
> Gunakan dengan bijak dan risiko sendiri.
