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

def tr_kucuk(metin: str) -> str:
    return metin.replace("İ", "i").replace("I", "ı").lower()

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
        "açık pozisyon", "işe alım ilanı", "kpss", "tercih kılavuzu", "kadrolarına"
    ])

def detay_cikar(baslik: str, domain: str):
    b = tr_kucuk(baslik)

    if any(k in b for k in ["hemşire", "sağlık", "paramedik", "ebe", "doktor", "tıbbi", "eczacı"]):
        kategori = "Sağlık Personeli"
    elif any(k in b for k in ["bilişim", "mühendis", "tekniker", "programcı", "yazılım", "siber"]):
        kategori = "Bilişim & Teknik"
    elif any(k in b for k in ["işçi", "temizlik", "şoför", "güvenlik", "hizmetli", "operatör", "koruma"]):
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

    return kategori, egitim, kpss, duz_mu, sehir, kontenjan, nitelik

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
                kategori, egitim, kpss, duz_mu, sehir, kontenjan, nitelik = detay_cikar(metin, domain)

                tum_ilanlar.append({
                    "id": f"ga-{idx}-{a_idx}",
                    "sourceDomain": domain,
                    "category": kategori,
                    "institution": domain.upper(),
                    "title": metin[:180],
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
                    "requirements": ["İlgili kurumun resmi duyuru metnindeki başvuru şartlarını inceleyiniz."],
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
