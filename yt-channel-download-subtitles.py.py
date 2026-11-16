#!/usr/bin/env python3
"""
Extracts subtitles from all videos of a YouTube channel
and saves them as clean text files (without timestamps).

Requirements:
    pip install -U yt-dlp

Examples:
    python yt-channel-download-subtitles.py https://www.youtube.com/@ChannelName
    python yt-channel-download-subtitles.py @ChannelName --languages it en --output subtitles
    python yt-channel-download-subtitles.py @ChannelName --cookies-browser firefox --pause 5
    python yt-channel-download-subtitles.py @ChannelName --no-auto --keep-vtt
"""

import argparse
import html
import re
import sys
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    sys.exit("Manca yt-dlp: installalo con  pip install -U yt-dlp")


def normalizza_url(canale: str) -> str:
    """Accetta URL completo, @handle, ID canale (UC...) o nome semplice."""
    canale = canale.strip()
    if canale.startswith("http"):
        return canale
    if canale.startswith("@"):
        return f"https://www.youtube.com/{canale}"
    if canale.startswith("UC") and len(canale) == 24:
        return f"https://www.youtube.com/channel/{canale}"
    return f"https://www.youtube.com/@{canale}"


TAG_RE = re.compile(r"<[^>]+>")
TIMESTAMP_RE = re.compile(r"^(\d{2}:)?\d{2}:\d{2}\.\d{3}\s+-->")
INTESTAZIONI = ("WEBVTT", "Kind:", "Language:", "NOTE", "STYLE")


def vtt_a_testo(percorso: Path) -> str:
    """Converte un file .vtt in testo semplice, eliminando timestamp,
    tag e le righe ripetute tipiche dei sottotitoli automatici."""
    righe = []
    ultima = None
    contenuto = percorso.read_text(encoding="utf-8", errors="replace")
    for riga in contenuto.splitlines():
        riga = riga.strip()
        if not riga or riga.startswith(INTESTAZIONI) or TIMESTAMP_RE.match(riga):
            continue
        riga = html.unescape(TAG_RE.sub("", riga)).strip()
        if riga and riga != ultima:
            righe.append(riga)
            ultima = riga
    return "\n".join(righe) + "\n"


def main():
    p = argparse.ArgumentParser(description="Scarica i sottotitoli di tutti i video di un canale YouTube.")
    p.add_argument("canale", help="URL del canale, @handle o ID (UC...)")
    p.add_argument("-l", "--lingue", nargs="+", default=["it", "en"],
                   help="codici lingua da cercare (default: it en). Usa 'all' per tutte")
    p.add_argument("-o", "--output", default="sottotitoli", help="cartella di destinazione")
    p.add_argument("--no-auto", action="store_true",
                   help="solo sottotitoli caricati dall'autore, niente generati automaticamente")
    p.add_argument("--tieni-vtt", action="store_true", help="conserva anche i .vtt originali con timestamp")
    p.add_argument("--pausa", type=float, default=3.0,
                   help="secondi di pausa tra un download e l'altro (contro il blocco 429)")
    p.add_argument("--cookies-browser",
                   help="usa i cookie del browser (firefox, chrome, edge...) se YouTube blocca le richieste")
    p.add_argument("--limite", type=int, help="elabora solo i primi N video (utile per provare)")
    args = p.parse_args()

    url = normalizza_url(args.canale)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    opzioni = {
        "skip_download": True,                 # niente video, solo sottotitoli
        "writesubtitles": True,
        "writeautomaticsub": not args.no_auto,
        "subtitleslangs": args.lingue,
        "subtitlesformat": "vtt/best",
        # Sottocartella col nome del canale (yt-dlp la crea da solo)
        "outtmpl": str(out / "%(channel,uploader)s" / "%(upload_date)s - %(title).120B [%(id)s].%(ext)s"),
        "download_archive": str(out / ".archivio.txt"),  # permette di riprendere senza rifare tutto
        "ignoreerrors": True,
        "sleep_interval_subtitles": args.pausa,
        "sleep_interval_requests": 1,
        "windowsfilenames": True,
    }
    if args.cookies_browser:
        opzioni["cookiesfrombrowser"] = (args.cookies_browser,)
    if args.limite:
        opzioni["playlistend"] = args.limite

    print(f"Canale: {url}\nDestinazione: {out.resolve()}\n")
    with yt_dlp.YoutubeDL(opzioni) as ydl:
        ydl.download([url])

    # Conversione dei .vtt in .txt puliti
    convertiti = 0
    cartelle = set()
    for vtt in sorted(out.rglob("*.vtt")):
        cartelle.add(vtt.parent)
        txt = vtt.with_suffix(".txt")
        if not txt.exists():
            txt.write_text(vtt_a_testo(vtt), encoding="utf-8")
            convertiti += 1
        if not args.tieni_vtt:
            vtt.unlink()

    print(f"\nFatto. {convertiti} nuovi file di testo.")
    for c in sorted(cartelle):
        print(f"  -> {c.resolve()}")


if __name__ == "__main__":
    main()
