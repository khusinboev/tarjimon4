"""
📝 Centralized 3-Language Message Dictionary
Format: Uzbek | Indonesian | English
"""

MSG = {
    # ===== USER HANDLERS =====
    "welcome": (
        "👋 <b>Tarjimon Botga Xush Kelibsiz!</b>\n"
        "Quyidagi menyudan kerakli bo'limni tanlang.\n\n"
        "👋 <b>Selamat Datang di Bot Penerjemah!</b>\n"
        "Pilih bagian dari menu di bawah.\n\n"
        "👋 <b>Welcome to Tarjimon Bot!</b>\n"
        "Select any section from menu below."
    ),
    
    "help": (
        "📚 <b>Qo'llanma</b>\n\n"
        "🔹 /lang — Tarjima tillarini tanlash\n"
        "🔹 Matn yuboring — Tanlangan tillarga tarjima\n"
        "🔹 Rasm: Caption matnini tarjima qiladi\n"
        "🔹 Ovoz: Tez orada qo'shiladi\n\n"
        "📚 <b>Panduan</b>\n\n"
        "🔹 /lang — Pilih bahasa terjemahan\n"
        "🔹 Kirim teks — Terjemahkan ke bahasa pilihan\n"
        "🔹 Gambar: Menerjemahkan teks caption\n"
        "🔹 Suara: Segera hadir\n\n"
        "📚 <b>Help</b>\n\n"
        "🔹 /lang — Select translation languages\n"
        "🔹 Send text — Translate to selected languages\n"
        "🔹 Image: Translates caption text\n"
        "🔹 Voice: Coming soon"
    ),
    
    "langs_loading_error": (
        "❌ <b>Tillarni yuklashda xatolik</b>\n"
        "Iltimos, keyinroq qayta urining.\n\n"
        "❌ <b>Kesalahan Memuat Bahasa</b>\n"
        "Silakan coba lagi nanti.\n\n"
        "❌ <b>Error Loading Languages</b>\n"
        "Please try again later."
    ),
    
    "blocked": (
        "🚫 <b>Siz admin tomonidan bloklangan.</b>\n"
        "Murojaat: @adkhambek_4\n\n"
        "🚫 <b>Anda telah diblokir oleh admin.</b>\n"
        "Hubungi: @adkhambek_4\n\n"
        "🚫 <b>You have been blocked by admin.</b>\n"
        "Contact: @adkhambek_4"
    ),
    
    "subscribe": (
        "📢 <b>Kanallarimizga obuna bo'ling</b>\n\n"
        "📢 <b>Berlangganan Saluran Kami</b>\n\n"
        "📢 <b>Subscribe to Our Channels</b>"
    ),
    
    # ===== LANGUAGE SELECTION =====
    "lang_title": (
        "🌐 <b>Tilni tanlang</b>\n"
        "✅ Chap: Kiruvchi | ✅ O'ng: Chiquvchi\n\n"
        "🌐 <b>Pilih Bahasa</b>\n"
        "✅ Kiri: Sumber | ✅ Kanan: Tujuan\n\n"
        "🌐 <b>Select Language</b>\n"
        "✅ Left: Source | ✅ Right: Target"
    ),
    
    "lang_updated": (
        "✅ Til yangilandi\n"
        "✅ Bahasa diperbarui\n"
        "✅ Language updated"
    ),
    
    "no_langs": (
        "⚠️ <b>Tillar tanlanmagan</b>\n"
        "➡️ /lang orqali tillarni tanlang\n\n"
        "⚠️ <b>Bahasa tidak dipilih</b>\n"
        "➡️ Pilih bahasa melalui /lang\n\n"
        "⚠️ <b>Languages not selected</b>\n"
        "➡️ Select via /lang command"
    ),
    
    "no_output_lang": (
        "❌ <b>Chiquvchi til tanlanmagan</b>\n"
        "➡️ /lang da o'ng ustundan tanlang\n\n"
        "❌ <b>Bahasa Output Tidak Dipilih</b>\n"
        "➡️ Pilih dari kolom kanan di /lang\n\n"
        "❌ <b>Output Language Not Selected</b>\n"
        "➡️ Select from right column in /lang"
    ),
    
    "auto_cannot_output": (
        "🚫 <b>Auto chiquvchi til bo'la olmaydi</b>\n"
        "➡️ O'ng ustundan boshqa til tanlang\n\n"
        "🚫 <b>Auto Tidak Bisa Jadi Bahasa Output</b>\n"
        "➡️ Pilih bahasa lain dari kolom kanan\n\n"
        "🚫 <b>Auto Cannot Be Output Language</b>\n"
        "➡️ Select another language from right"
    ),
    
    "langs_switched": (
        "🔄 <b>Tillar almashtirildi</b>\n"
        "🔄 <b>Bahasa Ditukar</b>\n"
        "🔄 <b>Languages Switched</b>"
    ),
    
    # ===== TRANSLATION =====
    "translate_error": (
        "❌ <b>Tarjima xatosi</b>\n"
        "🔄 Qayta urining\n\n"
        "❌ <b>Kesalahan Terjemahan</b>\n"
        "🔄 Coba lagi\n\n"
        "❌ <b>Translation Error</b>\n"
        "🔄 Try again"
    ),
    
    "translating": (
        "⏳ <b>Tarjima qilinmoqda...</b>\n"
        "⏳ <b>Menerjemahkan...</b>\n"
        "⏳ <b>Translating...</b>"
    ),
    
    # ===== ADMIN / BROADCAST =====
    "broadcast_starting": (
        "📬 <b>Xabar yuborilmoqda</b>\n"
        "Habar berish boshlandi...\n\n"
        "📬 <b>Mengirim Pesan</b>\n"
        "Pengiriman dimulai...\n\n"
        "📬 <b>Sending Message</b>\n"
        "Broadcast started..."
    ),
    
    "broadcast_sent": (
        "✅ <b>Xabar yuborildi</b>\n"
        "Jami: {total} | Yuborildi: {sent}\n\n"
        "✅ <b>Pesan Terkirim</b>\n"
        "Total: {total} | Terkirim: {sent}\n\n"
        "✅ <b>Message Sent</b>\n"
        "Total: {total} | Sent: {sent}"
    ),
    
    "broadcast_failed": (
        "❌ <b>Yuborish muvaffaqiyatsiz</b>\n"
        "Yuborilmagan: {failed} ta\n\n"
        "❌ <b>Pengiriman Gagal</b>\n"
        "Tidak terkirim: {failed} pesan\n\n"
        "❌ <b>Broadcast Failed</b>\n"
        "Failed: {failed} messages"
    ),
    
    # ===== SETTINGS / FEATURES =====
    "coming_soon": (
        "⏳ <b>Tez orada qo'shiladi</b>\n"
        "Ushbu funksiya hozircha mavjud emas.\n\n"
        "⏳ <b>Segera Hadir</b>\n"
        "Fitur ini akan segera tersedia.\n\n"
        "⏳ <b>Coming Soon</b>\n"
        "This feature will be available soon."
    ),
    
    "notifications_settings": (
        "🔔 <b>Bildirishnomalar</b>\n"
        "Bildirishnoma sozlamalarini o'zgartiring\n\n"
        "🔔 <b>Notifikasi</b>\n"
        "Ubah pengaturan notifikasi\n\n"
        "🔔 <b>Notifications</b>\n"
        "Change notification settings"
    ),
    
    "theme_settings": (
        "🎨 <b>Mavzu</b>\n"
        "Mavzu sozlamalarini tanlang\n\n"
        "🎨 <b>Tema</b>\n"
        "Pilih pengaturan tema\n\n"
        "🎨 <b>Theme</b>\n"
        "Choose theme settings"
    ),
    
    "sound_settings": (
        "🔊 <b>Ovoz</b>\n"
        "Ovoz sozlamalarini o'zgartiring\n\n"
        "🔊 <b>Suara</b>\n"
        "Ubah pengaturan suara\n\n"
        "🔊 <b>Sound</b>\n"
        "Change sound settings"
    ),
    
    "export_data": (
        "💾 <b>Ma'lumotni eksport qilish</b>\n"
        "Barcha tarjimalarini yuklab oling\n\n"
        "💾 <b>Ekspor Data</b>\n"
        "Unduh semua terjemahan Anda\n\n"
        "💾 <b>Export Data</b>\n"
        "Download all your translations"
    ),
    
    "delete_account": (
        "⚠️ <b>Akkauntni o'chirish</b>\n"
        "Bu amalni qaytarib bo'lmaydi!\n\n"
        "⚠️ <b>Hapus Akun</b>\n"
        "Tindakan ini tidak dapat dibatalkan!\n\n"
        "⚠️ <b>Delete Account</b>\n"
        "This action cannot be undone!"
    ),
    
    # ===== STATS =====
    "stats_header": (
        "📊 <b>Statistika</b>\n\n"
        "📊 <b>Statistik</b>\n\n"
        "📊 <b>Statistics</b>"
    ),
    
    "total_users": (
        "👥 Jami foydalanuvchilar: {count}\n"
        "👥 Total pengguna: {count}\n"
        "👥 Total users: {count}"
    ),
    
    "total_translations": (
        "📝 Jami tarjimalar: {count}\n"
        "📝 Total terjemahan: {count}\n"
        "📝 Total translations: {count}"
    ),
}
