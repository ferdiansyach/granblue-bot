# 🤖 Granblue Automation — v3.1.1

> A Python-based automation bot for **Granblue Fantasy** (browser).  
> Uses computer vision (OpenCV + EasyOCR) and automated mouse/keyboard control.

---

## ⚠️ Terms of Use

**Read and understand the following before using this project:**

1. **Personal & educational use only.**  
   This project was created as an automation experiment and learning exercise. Commercial use or resale in any form is strictly prohibited.

2. **You bear all account risks.**  
   Using bots in online games may violate Cygames' Terms of Service. Any consequences such as **bans, suspensions, or account deletion** are solely your responsibility. The developer is not liable for any losses.

3. **No unauthorized redistribution.**  
   Spreading, selling, or forking this project without explicit permission from the repository owner is prohibited.

4. **No warranty.**  
   This software is provided "as-is" without any guarantee. The developer does not guarantee it will run perfectly on all systems or conditions.

5. **Protect your privacy & security.**  
   Never share your `settings.json` file publicly as it contains sensitive API tokens (Twitter, Discord).

6. **Use responsibly.**  
   Avoid actions that could harm other players (e.g., flooding raid rooms, monopolizing resources).

---

## 📋 Project Description

Granblue Automation is a bot capable of automatically running various battle modes in Granblue Fantasy using:

- **Computer Vision** — Game element detection via screenshots using OpenCV & template matching
- **OCR** — On-screen text reading via EasyOCR
- **Mouse & Keyboard Automation** — Automated control via PyAutoGUI with Bezier curve mouse movements
- **Multi-process** — Bot runs in a separate process to avoid blocking the UI
- **Notifications** — Discord & Twitter integration for real-time alerts

---

## 🎮 Supported Modes

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

## 🛠️ System Requirements

| Component | Requirement |
|---|---|
| OS | Windows 10/11 (64-bit) |
| Python | 3.9+ |
| GPU | NVIDIA with CUDA 11.6 (for PyTorch) |
| RAM | Minimum 8 GB |
| Browser | Chrome/Edge with Granblue Fantasy active |
| Resolution | Adjusted via `customScale` setting |

---

## 📦 Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/<username>/<repo-name>.git
cd <repo-name>
```

### 2. Create a virtual environment

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** PyTorch (`torch`, `torchvision`, `torchaudio`) will be downloaded from the PyTorch server and requires a stable internet connection. File size is quite large (~2 GB).

### 4. Configure `settings.json`

Edit the `backend/settings.json` file. **Do not commit this file to Git** (already excluded via `.gitignore`).

Main configuration:

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

### 5. Run the bot

```bash
cd backend
python main.py
```

Or use the executable directly:

```bash
"Granblue Automation.exe"
```

---

## ⚙️ Advanced Configuration

### Combat Script

Create a `.txt` file in the `scripts/` folder to define the order of combat actions. Example format (`full_auto.txt`):

```
Turn 1:
enableFullAuto
end
```

See existing example scripts in the `scripts/` folder for further reference.

### Discord Notifications

Enable in `settings.json`:

```json
"discord": {
  "enableDiscordNotifications": true,
  "discordToken": "YOUR_BOT_TOKEN",
  "discordUserID": "YOUR_USER_ID"
}
```

### Twitter Notifications

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

## 📁 Project Structure

```
Granblue.Automation.v3.1.1/
├── backend/
│   ├── bot/
│   │   ├── game.py              # Core game logic
│   │   ├── combat_mode.py       # Combat mode handler
│   │   ├── dom_clicker.py       # Browser DOM control
│   │   ├── window.py            # Window management
│   │   └── game_modes/          # Modules for each farming mode
│   ├── model/                   # ML models (if any)
│   ├── utils/                   # Utilities (logging, image, etc.)
│   ├── main.py                  # Entry point
│   ├── requirements.txt         # Python dependencies
│   └── settings.json            # Configuration (DO NOT commit!)
├── images/                      # Template images for detection
├── scripts/                     # Custom combat scripts (.txt)
├── logs/                        # Bot session logs (ignored by Git)
└── README.md                    # This documentation
```

---

## 🐛 Debugging & Troubleshooting

- Enable `"debugMode": true` in `settings.json` for more detailed logs.
- Logs are saved in the `logs/` folder and excluded from Git.
- If the bot fails to detect elements correctly, try adjusting:
  - `"confidence"` and `"confidenceAll"` in the `device` section
  - `"customScale"` to match your monitor resolution
  - `adjustment` values for fine-tuning timing

---

## 🤝 Contributing

Pull requests are welcome for:
- Bug fixes
- New farming mode additions
- Improved detection accuracy

Ensure submitted code:
1. Contains no tokens or secrets
2. Follows the existing code style (docstrings, type hints)
3. Includes a change description in the PR description

---

## 📄 License

This project has **no official open-source license**.  
Use is limited to **personal and educational purposes** only.  
Redistribution and commercial use are **prohibited** without written permission from the owner.

---

## ⚡ Disclaimer

> This project is **not affiliated with, sponsored by, or endorsed by** Cygames, Inc.  
> "Granblue Fantasy" is a trademark of Cygames, Inc.  
> Use wisely and at your own risk.

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
