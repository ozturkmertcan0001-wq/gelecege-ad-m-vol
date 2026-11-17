import json
import re
import time
import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import schedule

PORTALLAR = [
    ("kamuilan.sbb.gov.tr", "https://kamuilan.sbb.gov.tr"),
    ("kariyerkapisi.gov.tr", "https://kariyerkapisi.gov.tr"),
    ("isealimkariyerkapisi.cbiko.gov.tr", "https://isealimkariyerkapisi.cbiko.gov.tr"),
    ("osym.gov.tr", "https://www.osym.gov.tr"),
    ("iskur.gov.tr", "https://www.iskur.gov.tr"),
    ("resmigazete.gov.tr", "https://www.resmigazete.gov.tr"),
    ("ilan.gov.tr", "https://www.ilan.gov.tr"),
    ("yerelyonetimler.csb.gov.tr", "https://yerelyonetimler.csb.gov.tr"),
    ("kariyer.ibb.istanbul", "https://kariyer.ibb.istanbul/ilanlar"),
    ("kariyer.ankara.bel.tr", "https://kariyer.ankara.bel.tr"),
    ("izmir.bel.tr", "https://www.izmir.bel.tr/tr/Duyurular"),
    ("dsi.gov.tr", "https://www.dsi.gov.tr/Duyurular"),
    ("kgm.gov.tr", "https://www.kgm.gov.tr/Sayfalar/KGM/SiteTr/Kurumsal/Duyurular.aspx"),
    ("botas.gov.tr", "https://www.botas.gov.tr/Duyurular"),
    ("tpao.gov.tr", "https://www.tpao.gov.tr/duyurular"),
    ("dhmi.gov.tr", "https://www.dhmi.gov.tr/Sayfalar/Duyurular.aspx"),
    ("kariyer.thy.com", "https://kariyer.thy.com"),
    ("tcdd.gov.tr", "https://www.tcdd.gov.tr/duyurular"),
    ("teias.gov.tr", "https://www.teias.gov.tr/duyurular"),
    ("ptt.gov.tr", "https://www.ptt.gov.tr/duyurular"),
    ("gib.gov.tr", "https://www.gib.gov.tr/duyurular"),
    ("sgk.gov.tr", "https://www.sgk.gov.tr/Duyuru"),
    ("aile.gov.tr", "https://www.aile.gov.tr/duyurular"),
    ("tarimorman.gov.tr", "https://www.tarimorman.gov.tr/Duyurular"),
    ("yhgm.saglik.gov.tr", "https://yhgm.saglik.gov.tr"),
    ("personel.meb.gov.tr", "https://personel.meb.gov.tr"),
    ("pgm.adalet.gov.tr", "https://pgm.adalet.gov.tr"),
    ("personeltemin.msb.gov.tr", "https://personeltemin.msb.gov.tr"),
    ("personeltemin.jandarma.gov.tr", "https://personeltemin.jandarma.gov.tr"),
    ("pa.edu.tr", "https://www.pa.edu.tr"),
    ("yok.gov.tr", "https://www.yok.gov.tr"),
    ("kariyer.tubitak.gov.tr", "https://kariyer.tubitak.gov.tr"),
    ("vizyonergenc.com", "https://vizyonergenc.com"),
    ("aselsan.com", "https://www.aselsan.com/tr/kariyer"),
    ("tusas.com", "https://www.tusas.com/kariyer"),
    ("roketsan.com.tr", "https://www.roketsan.com.tr/tr/kariyer"),
    ("kizilaykariyer.com", "https://www.kizilaykariyer.com"),
    ("ziraatbank.com.tr", "https://www.ziraatbank.com.tr/tr/bankamiz/insan-kaynaklari/acik-pozisyonlar"),
    ("halkbank.com.tr", "https://www.halkbank.com.tr/tr/bankamiz/insan-kaynaklari.html"),
    ("vakifbank.com.tr", "https://www.vakifbank.com.tr/insan-kaynaklari.aspx?pageID=203"),
    ("tcmb.gov.tr", "https://insankaynaklari.tcmb.gov.tr"),
    ("bddk.org.tr", "https://www.bddk.org.tr/Duyurular"),
]

HARIC_TUTULACAKLAR = [
    "ihale", "zeyilname", "sonuç ilanı", "sonuç duyurusu", "sonuçları",
    "giriş belgesi", "sınav takvimi", "etik ilkeleri", "daire başkanlığı",
    "rehberleri", "taslakları", "yer değiştirme", "mazerete bağlı",
    "görevde yükselme", "unvan değişikliği", "cübbe", "2024", "2025"
]

SEHIRLER = [
    "Ankara", "İstanbul", "İzmir", "Antalya", "Bursa", "Adana", "Konya",
    "Gaziantep", "Samsun", "Trabzon", "Şanlıurfa", "Batman", "Diyarbakır",
    "Mersin", "Kayseri", "Eskişehir", "Kocaeli", "Sakarya", "Manisa", "Van"
]

# İstenen meslek / unvan eşleştirme sözlüğü (95+ meslek - spesifikten genele sıralı)
MESLEK_SOZLUGU = [
    # Sağlık & Sosyal Hizmetler
    ("psikolog", "Psikolog"),
    ("sosyal çalışmacı", "Sosyal Çalışmacı"),
    ("sosyolog", "Sosyolog"),
    ("çocuk gelişimcisi", "Çocuk Gelişimcisi"),
    ("çocuk gelişimi", "Çocuk Gelişimcisi"),
    ("hemşire", "Hemşire"),
    ("ebe", "Ebe"),
    ("paramedik", "Paramedik (İlk ve Acil Yardım)"),
    ("ilk ve acil yardım", "Paramedik (İlk ve Acil Yardım)"),
    ("acil tıp teknisyeni", "Acil Tıp Teknisyeni (ATT)"),
    ("tıbbi sekreter", "Tıbbi Sekreter"),
    ("fizyoterapist", "Fizyoterapist"),
    ("diyetisyen", "Diyetisyen"),
    ("odyolog", "Odyolog"),
    ("ergoterapist", "Ergoterapist"),
    ("dil ve konuşma terapisti", "Dil ve Konuşma Terapisti"),
    ("perfüzyonist", "Perfüzyonist"),
    ("eczacı", "Eczacı"),
    ("diş tabibi", "Diş Tabibi"),
    ("diş hekimi", "Diş Tabibi"),
    ("tabip", "Tabip / Doktor"),
    ("doktor", "Tabip / Doktor"),
    ("veteriner", "Veteriner Hekim"),
    ("biyolog", "Biyolog"),
    ("kimyager", "Kimyager"),
    ("laborant", "Laborant"),
    ("tıbbi görüntüleme", "Tıbbi Görüntüleme (Röntgen)"),
    ("röntgen", "Tıbbi Görüntüleme (Röntgen)"),
    ("anestezi", "Anestezi Teknikeri"),
    ("diyaliz", "Diyaliz Teknikeri"),
    ("ameliyathane", "Ameliyathane Teknikeri"),
    ("ağız ve diş sağlığı", "Ağız ve Diş Sağlığı Teknikeri"),
    ("optisyen", "Optisyen"),
    ("sağlık teknikeri", "Sağlık Teknikeri"),
    ("sağlık personeli", "Sağlık Personeli"),

    # Mühendislik, Mimarlık & Fen Bilimleri (Spesifik dallar önce)
    ("makine mühendisi", "Makine Mühendisi"),
    ("makina mühendisi", "Makine Mühendisi"),
    ("inşaat mühendisi", "İnşaat Mühendisi"),
    ("elektrik-elektronik mühendisi", "Elektrik-Elektronik Mühendisi"),
    ("elektrik elektronik mühendisi", "Elektrik-Elektronik Mühendisi"),
    ("elektrik mühendisi", "Elektrik Mühendisi"),
    ("elektronik mühendisi", "Elektronik Mühendisi"),
    ("bilgisayar mühendisi", "Bilgisayar Mühendisi"),
    ("yazılım mühendisi", "Yazılım Mühendisi"),
    ("endüstri mühendisi", "Endüstri Mühendisi"),
    ("çevre mühendisi", "Çevre Mühendisi"),
    ("gıda mühendisi", "Gıda Mühendisi"),
    ("ziraat mühendisi", "Ziraat Mühendisi"),
    ("orman mühendisi", "Orman Mühendisi"),
    ("harita mühendisi", "Harita Mühendisi"),
    ("jeoloji mühendisi", "Jeoloji Mühendisi"),
    ("jeofizik mühendisi", "Jeofizik Mühendisi"),
    ("maden mühendisi", "Maden Mühendisi"),
    ("metalurji ve malzeme mühendisi", "Metalurji ve Malzeme Mühendisi"),
    ("kimya mühendisi", "Kimya Mühendisi"),
    ("mekatronik mühendisi", "Mekatronik Mühendisi"),
    ("uçak mühendisi", "Uçak / Havacılık Mühendisi"),
    ("havacılık mühendisi", "Uçak / Havacılık Mühendisi"),
    ("otomotiv mühendisi", "Otomotiv Mühendisi"),
    ("biyomedikal mühendisi", "Biyomedikal Mühendisi"),
    ("enerji sistemleri mühendisi", "Enerji Sistemleri Mühendisi"),
    ("mühendis", "Mühendis"),
    ("iç mimar", "İç Mimar"),
    ("peyzaj mimarı", "Peyzaj Mimarı"),
    ("mimar", "Mimar"),
    ("şehir plancısı", "Şehir Plancısı"),
    ("istatistikçi", "İstatistikçi"),
    ("matematikçi", "Matematikçi"),
    ("fizikçi", "Fizikçi"),

    # Büro, Adalet, Finans & Kültür
    ("büro personeli", "Büro Personeli"),
    ("düz memur", "Düz Memur"),
    ("veri hazırlama", "VHKİ (Veri Hazırlama)"),
    ("zabıt katibi", "Zabıt Katibi"),
    ("zabıt kâtibi", "Zabıt Katibi"),
    ("mübaşir", "Mübaşir"),
    ("icra katibi", "İcra Katibi"),
    ("icra kâtibi", "İcra Katibi"),
    ("infaz ve koruma memuru", "İnfaz ve Koruma Memuru"),
    ("avukat", "Avukat"),
    ("mütercim", "Mütercim-Tercüman"),
    ("tercüman", "Mütercim-Tercüman"),
    ("kütüphaneci", "Kütüphaneci"),
    ("arkeolog", "Arkeolog"),
    ("sanat tarihçisi", "Sanat Tarihçisi"),
    ("müze araştırmacısı", "Müze Araştırmacısı"),
    ("restoratör", "Restoratör"),
    ("gişe", "Gişe / Servis Görevlisi"),
    ("servis görevlisi", "Servis Görevlisi"),
    ("veznedar", "Veznedar"),
    ("çağrı merkezi", "Çağrı Merkezi Personeli"),
    ("sekreter", "Sekreter"),
    ("muhasebeci", "Muhasebeci"),

    # Bilişim & Tekniker / Teknisyen
    ("bilişim personeli", "Sözleşmeli Bilişim Personeli"),
    ("yazılım uzmanı", "Yazılım Uzmanı"),
    ("siber güvenlik", "Siber Güvenlik Uzmanı"),
    ("sistem uzmanı", "Sistem / Ağ Uzmanı"),
    ("ağ uzmanı", "Sistem / Ağ Uzmanı"),
    ("veritabanı uzmanı", "Veritabanı Uzmanı"),
    ("programcı", "Programcı"),
    ("bilgisayar teknikeri", "Bilgisayar Teknikeri"),
    ("elektrik teknikeri", "Elektrik Teknikeri"),
    ("elektronik teknikeri", "Elektronik Teknikeri"),
    ("makine teknikeri", "Makine Teknikeri"),
    ("inşaat teknikeri", "İnşaat Teknikeri"),
    ("harita teknikeri", "Harita Teknikeri"),
    ("otomotiv teknikeri", "Otomotiv Teknikeri"),
    ("iklimlendirme", "İklimlendirme Teknikeri"),
    ("tekniker", "Tekniker"),
    ("teknisyen", "Teknisyen"),

    # İşçi, Güvenlik & Destek Hizmetleri
    ("koruma ve güvenlik", "Koruma ve Güvenlik Görevlisi"),
    ("güvenlik görevlisi", "Koruma ve Güvenlik Görevlisi"),
    ("destek personeli", "Destek Personeli"),
    ("temizlik", "Temizlik Görevlisi"),
    ("şoför", "Şoför"),
    ("aşçı", "Aşçı"),
    ("bahçıvan", "Bahçıvan"),
    ("kaloriferci", "Kaloriferci"),
    ("elektrikçi", "Elektrikçi"),
    ("sıhhi tesisat", "Sıhhi Tesisatçı"),
    ("marangoz", "Marangoz"),
    ("kaynakçı", "Kaynakçı"),
    ("boyacı", "Boyacı"),
    ("operatör", "İş Makinesi Operatörü"),
    ("bakım", "Bakım-Onarım Personeli"),
    ("sürekli işçi", "Sürekli İşçi"),
    ("işçi alım", "Kamu İşçisi"),

    # Uzman, Denetim & Akademik
    ("gelir uzman yardımcısı", "Gelir Uzman Yardımcısı"),
    ("vergi müfettiş yardımcısı", "Vergi Müfettiş Yardımcısı"),
    ("uzman yardımcısı", "Uzman Yardımcısı"),
    ("müfettiş yardımcısı", "Müfettiş Yardımcısı"),
    ("denetmen yardımcısı", "Denetmen Yardımcısı"),
    ("kontrolör yardımcısı", "Kontrolör Yardımcısı"),
    ("öğretim görevlisi", "Öğretim Görevlisi"),
    ("araştırma görevlisi", "Araştırma Görevlisi"),
    ("öğretim üyesi", "Öğretim Üyesi"),
    ("öğretmen", "Öğretmen"),
]


def tr_kucuk(metin: str) -> str:
    return metin.replace("İ", "i").replace("I", "ı").lower()


def meslekleri_cikar(metin: str, kategori: str = "") -> tuple:
    """
    Başlık ve ilan detay metninden istenen tüm meslek/unvanları ve varsa
    meslek bazlı kontenjan sayılarını çıkarır.
    Dönüş: (temiz_meslek_listesi, detayli_meslek_listesi)
    """
    b = tr_kucuk(metin)
    bulunanlar = []
    detayli = []

    for anahtar, unvan in MESLEK_SOZLUGU:
        # Kısa kelimeler için kelime sınırı kontrolü (örn: 'ebe', 'aşçı', 'mimar')
        if len(anahtar) <= 5:
            desen = r"\b" + re.escape(anahtar) + r"(?:i|ı|u|ü|ler|lar|leri|ları)?\b"
            eslesme_var = re.search(desen, b) is not None
        else:
            eslesme_var = anahtar in b

        if eslesme_var and unvan not in bulunanlar:
            # Spesifik mühendislik/mimarlık/teknikerlik varsa genel etiketi ekleme
            if unvan == "Mühendis" and any("Mühendisi" in u for u in bulunanlar):
                continue
            if unvan == "Mimar" and any(u in ("İç Mimar", "Peyzaj Mimarı") for u in bulunanlar):
                continue
            if unvan == "Tekniker" and any("Teknikeri" in u for u in bulunanlar):
                continue

            bulunanlar.append(unvan)

            # Mesleğin hemen önünde veya arkasında kontenjan sayısı varsa yakala (örn: "15 psikolog", "psikolog (15)", "psikolog 15")
            k_desen_on = re.search(r"\b(\d{1,4})\s*(?:adet|kişi)?\s*" + re.escape(anahtar), b)
            k_desen_arka = re.search(re.escape(anahtar) + r"(?:i|ı|u|ü|ler|lar|leri|ları)?\s*[\(\[\:\-\|]?\s*(\d{1,4})\s*(?:adet|kişi|kadro)?[\)\]]?", b)
            adet = None
            if k_desen_on:
                sayi = int(k_desen_on.group(1))
                if 1 <= sayi <= 25000 and sayi not in (2001, 3001, 4001, 2024, 2025, 2026):
                    adet = sayi
            elif k_desen_arka:
                sayi = int(k_desen_arka.group(1))
                if 1 <= sayi <= 25000 and sayi not in (2001, 3001, 4001, 2024, 2025, 2026):
                    adet = sayi

            detayli.append(f"{unvan} ({adet})" if adet else unvan)

        if len(bulunanlar) >= 25:
            break

    if not bulunanlar:
        if "sözleşmeli personel" in b:
            fallback = "Sözleşmeli Personel (Çeşitli Unvanlar)"
        elif "memur alım" in b:
            fallback = "Memur (Genel İdare / Meslek)"
        elif kategori == "Sağlık Personeli":
            fallback = "Sağlık Personeli"
        elif kategori == "Bilişim & Teknik":
            fallback = "Teknik / Bilişim Personeli"
        elif kategori == "İşçi & Hizmetli":
            fallback = "Sürekli İşçi / Destek Personeli"
        elif kategori == "Uzman & Akademik":
            fallback = "Uzman / Akademik Personel"
        else:
            fallback = "Büro / İdari Personel"
        bulunanlar.append(fallback)
        detayli.append(fallback)

    return bulunanlar, detayli


def gercek_ilan_mi(baslik: str, url: str) -> bool:
    b = tr_kucuk(baslik)
    u = url.lower()
    if len(baslik) < 28 or any(h in b for h in HARIC_TUTULACAKLAR):
        return False
    if u.endswith("#") or "javascript:" in u:
        return False
    return any(k in b for k in [
        "personel alım", "memur alım", "işçi alım", "sözleşmeli personel",
        "uzman yardımcısı", "müfettiş yardımcısı", "zabıt katibi", "mübaşir",
        "bilişim personeli", "sağlık personeli", "hemşire", "paramedik",
        "psikolog", "mühendis", "açık pozisyon", "işe alım ilanı",
        "kpss", "tercih kılavuzu", "kadrolarına"
    ])


def detay_cikar(baslik: str, domain: str):
    b = tr_kucuk(baslik)

    if any(k in b for k in ["hemşire", "sağlık", "paramedik", "ebe", "doktor", "tıbbi", "eczacı", "psikolog", "fizyoterapist", "diyetisyen"]):
        kategori = "Sağlık Personeli"
    elif any(k in b for k in ["bilişim", "mühendis", "mimar", "tekniker", "teknisyen", "programcı", "yazılım", "siber"]):
        kategori = "Bilişim & Teknik"
    elif any(k in b for k in ["işçi", "temizlik", "şoför", "güvenlik", "hizmetli", "operatör", "koruma", "aşçı", "kaloriferci"]):
        kategori = "İşçi & Hizmetli"
    elif any(k in b for k in ["uzman", "müfettiş", "öğretim", "araştırma", "akademik", "denetmen"]):
        kategori = "Uzman & Akademik"
    else:
        kategori = "Büro & İdari"

    if any(k in b for k in ["2001", "ortaöğretim", "lise"]):
        egitim, kpss = "Ortaöğretim", "KPSS P94 (Ortaöğretim)"
    elif any(k in b for k in ["3001", "önlisans", "ön lisans", "tekniker", "paramedik"]):
        egitim, kpss = "Önlisans", "KPSS P93 (Önlisans)"
    elif any(k in b for k in ["ilköğretim", "sürekli işçi", "işçi alım"]):
        egitim, kpss = "İlköğretim", "KPSS Şartsız"
    else:
        egitim, kpss = "Lisans", "KPSS P3 (Lisans)"

    if any(k in domain for k in ["ibb.istanbul", "ankara.bel.tr", "thy.com", "aselsan", "tusas", "roketsan", "bank"]):
        kpss = "KPSS Şartsız"

    duz_mu = any(k in b for k in [
        "4001", "3001", "2001", "bölüm şartsız", "herhangi bir lisans",
        "herhangi bir önlisans", "düz memur", "büro personeli",
        "zabıt katibi", "mübaşir", "gişe", "servis görevlisi", "destek personeli"
    ])

    sehir = "Türkiye Geneli"
    if "ibb.istanbul" in domain:
        sehir = "İstanbul"
    elif "ankara.bel.tr" in domain:
        sehir = "Ankara"
    elif "izmir.bel.tr" in domain:
        sehir = "İzmir"
    else:
        for s in SEHIRLER:
            if tr_kucuk(s) in b:
                sehir = s
                break

    eslesme = re.search(r"\b(\d{1,5})\s*(?:sözleşmeli|sürekli|memur|personel|işçi|uzman|kadro|kişilik)", b)
    kontenjan = int(eslesme.group(1)) if eslesme else 1

    if "2001" in b:
        nitelik = "2001 (Lise - Bölüm Şartsız)"
    elif "3001" in b:
        nitelik = "3001 (Önlisans - Bölüm Şartsız)"
    elif "4001" in b or duz_mu:
        nitelik = "4001 (Bölüm Şartsız)"
    else:
        nitelik = "Özel Nitelik"

    meslekler, detayli_meslekler = meslekleri_cikar(baslik, kategori)
    return kategori, egitim, kpss, duz_mu, sehir, kontenjan, nitelik, meslekler, detayli_meslekler


def ilan_sayfasi_zenginlestir(url: str, headers: dict, mevcut_baslik: str, kategori: str, mevcut_kontenjan: int):
    """İlan detay sayfasındaki metin ve kadro tablolarını okuyarak istenen tüm meslekleri çıkarır."""
    if url.lower().endswith((".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".rar")):
        return None
    try:
        r = requests.get(url, headers=headers, timeout=6)
        if r.status_code != 200:
            return None
        if not r.encoding or r.encoding.lower() == "iso-8859-1":
            r.encoding = r.apparent_encoding or "utf-8"
        s = BeautifulSoup(r.text, "html.parser")
        for tag in s(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        # Tablo satırları ve liste öğeleri dahil tüm gövde metnini al (25.000 karaktere kadar)
        govde = " ".join(s.get_text(" ").split())
        if len(govde) < 80:
            return None

        meslekler, detayli_meslekler = meslekleri_cikar(f"{mevcut_baslik} {govde[:25000]}", kategori)

        # Sayfadaki kadro/pozisyon tablolarından ham unvan satırlarını da çek
        kadro_satirlari = []
        for tr in s.find_all("tr"):
            hucreler = [" ".join(td.get_text().split()) for td in tr.find_all(["td", "th"]) if td.get_text(strip=True)]
            if 2 <= len(hucreler) <= 8:
                satir = " — ".join(hucreler[:4])
                if 8 <= len(satir) <= 140 and any(k in tr_kucuk(satir) for k in [
                    "mühendis", "psikolog", "hemşire", "paramedik", "tekniker", "teknisyen",
                    "büro", "memur", "işçi", "şoför", "güvenlik", "uzman", "avukat", "tabip",
                    "ebe", "diyetisyen", "fizyoterapist", "katibi", "kâtibi", "mübaşir", "unvan", "kadro"
                ]):
                    if satir not in kadro_satirlari:
                        kadro_satirlari.append(satir)
            if len(kadro_satirlari) >= 15:
                break

        yeni_kontenjan = mevcut_kontenjan
        if mevcut_kontenjan <= 1:
            m = re.search(r"\b(\d{1,5})\s*(?:adet|kişi|kadro|sözleşmeli personel|sürekli işçi|memur)\b", tr_kucuk(govde[:5000]))
            if m:
                sayi = int(m.group(1))
                if 1 <= sayi <= 50000:
                    yeni_kontenjan = sayi

        cumleler = [c.strip() for c in re.split(r"[.!?]\s+", govde[:3000]) if 35 <= len(c.strip()) <= 240]
        ilgili_cumleler = [
            c for c in cumleler
            if any(k in tr_kucuk(c) for k in ["alım", "başvuru", "kpss", "personel", "kadro", "unvan", "mezun", "psikolog", "mühendis"])
        ][:2]

        return {
            "positions": meslekler,
            "positionDetails": detayli_meslekler,
            "kadroRows": kadro_satirlari,
            "quota": yeni_kontenjan,
            "requirements": ilgili_cumleler
        }
    except Exception:
        return None


def portallari_tara():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 42 resmi portal taranıyor...")
    tum_ilanlar = []
    gorulen_url = set()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9"
    }

    for idx, (domain, base_url) in enumerate(PORTALLAR):
        try:
            resp = requests.get(base_url, headers=headers, timeout=15)
            if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
                resp.encoding = resp.apparent_encoding or "utf-8"

            soup = BeautifulSoup(resp.text, "html.parser")
            portal_sayac = 0

            for a_idx, link in enumerate(soup.find_all("a", href=True)):
                metin = " ".join(link.get_text().split()).strip()
                tam_url = urljoin(base_url, link["href"].strip())

                if tam_url in gorulen_url or not gercek_ilan_mi(metin, tam_url):
                    continue

                gorulen_url.add(tam_url)
                kategori, egitim, kpss, duz_mu, sehir, kontenjan, nitelik, meslekler, detayli_meslekler = detay_cikar(metin, domain)
                sartlar = ["İlgili kurumun resmi duyuru metnindeki başvuru şartlarını inceleyiniz."]
                kadro_satirlari = []

                # Eşleşen tüm ilanların detay sayfasına girip istenen meslek listesini zenginleştir
                zengin = ilan_sayfasi_zenginlestir(tam_url, headers, metin, kategori, kontenjan)
                if zengin:
                    if zengin.get("positions"):
                        meslekler = zengin["positions"]
                    if zengin.get("positionDetails"):
                        detayli_meslekler = zengin["positionDetails"]
                    if zengin.get("kadroRows"):
                        kadro_satirlari = zengin["kadroRows"]
                    if zengin.get("quota"):
                        kontenjan = zengin["quota"]
                    if zengin.get("requirements"):
                        sartlar = zengin["requirements"]

                tum_ilanlar.append({
                    "id": f"ga-{idx}-{a_idx}",
                    "sourceDomain": domain,
                    "category": kategori,
                    "institution": domain.upper(),
                    "title": metin[:180],
                    "positions": meslekler,
                    "positionDetails": detayli_meslekler,
                    "kadroRows": kadro_satirlari,
                    "city": sehir,
                    "education": egitim,
                    "kpss": kpss,
                    "quota": kontenjan,
                    "publishDate": datetime.now().strftime("%Y-%m-%d"),
                    "endDate": (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d"),
                    "refNo": f"GA-{idx+1}-{a_idx+100}",
                    "qualCode": nitelik,
                    "isDuzMemurluk": duz_mu,
                    "url": tam_url,
                    "requirements": sartlar,
                    "documents": ["e-Devlet Mezuniyet Belgesi", "KPSS Sonuç Belgesi"]
                })
                portal_sayac += 1
                if portal_sayac >= 8:
                    break
        except Exception as hata:
            print(f"Uyarı ({domain}): {hata}")

    if tum_ilanlar:
        with open("ilanlar.json", "w", encoding="utf-8") as f:
            json.dump(tum_ilanlar, f, ensure_ascii=False, indent=2)
        print(f"Tamamlandı: {len(tum_ilanlar)} doğrulanmış ilan 'ilanlar.json' dosyasına yazıldı.")
    else:
        print("Uyarı: Yeni ilan çekilemedi, mevcut ilanlar.json korundu.")


class CORSHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()


if __name__ == "__main__":
    portallari_tara()
    schedule.every().hour.at(":00").do(portallari_tara)
    threading.Thread(
        target=lambda: HTTPServer(("0.0.0.0", 8000), CORSHandler).serve_forever(),
        daemon=True
    ).start()
    print("Canlı JSON sunucusu aktif: http://localhost:8000/ilanlar.json")
    while True:
        schedule.run_pending()
        time.sleep(15)
