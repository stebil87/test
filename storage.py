from supabase import create_client
from datetime import datetime
import config
import json

supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)


def salva_compilazione(nome: str, cognome: str, vf: bool,
                       pdf_files: dict, dati: dict,
                       doc_identita: list = None,
                       permesso_files: list = None):
    try:
        import time
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        cartella = f"{cognome}_{nome}_{ts}"

        # Salva PDF
        for nome_file, contenuto in pdf_files.items():
            path = f"{cartella}/{nome_file}"
            supabase.storage.from_(config.SUPABASE_BUCKET).upload(
                path=path,
                file=contenuto,
                file_options={"content-type": "application/pdf"}
            )
            time.sleep(0.5)

        # Salva documenti identità
        doc_paths = []
        if doc_identita:
            for i, (nome_file, contenuto, mime) in enumerate(doc_identita):
                path = f"{cartella}/identita_{i}_{nome_file}"
                supabase.storage.from_(config.SUPABASE_BUCKET).upload(
                    path=path,
                    file=contenuto,
                    file_options={"content-type": mime}
                )
                doc_paths.append(path)
                time.sleep(0.5)

        # Salva permesso G
        perm_paths = []
        if permesso_files:
            for i, (nome_file, contenuto, mime) in enumerate(permesso_files):
                path = f"{cartella}/permesso_{i}_{nome_file}"
                supabase.storage.from_(config.SUPABASE_BUCKET).upload(
                    path=path,
                    file=contenuto,
                    file_options={"content-type": mime}
                )
                perm_paths.append(path)
                time.sleep(0.5)

        supabase.table("compilazioni").insert({
            "nome":               nome,
            "cognome":            cognome,
            "vf":                 vf,
            "percorso":           cartella,
            "doc_identita_paths": doc_paths,
            "permesso_paths":     perm_paths,
            "dati_json":          json.dumps(dati, ensure_ascii=False),
            "modificato":         False,
        }).execute()

        return None

    except Exception as e:
        return str(e)


def aggiorna_compilazione(rid: int, dati: dict, pdf_files: dict, percorso: str):
    """Salva i PDF rigenerati come versione modificata e aggiorna i dati."""
    try:
        for nome_file, contenuto in pdf_files.items():
            path = f"{percorso}/mod_{nome_file}"
            # Prima prova a eliminare se esiste
            try:
                supabase.storage.from_(config.SUPABASE_BUCKET).remove(
                    [path])
            except Exception:
                pass
            supabase.storage.from_(config.SUPABASE_BUCKET).upload(
                path=path,
                file=contenuto,
                file_options={"content-type": "application/pdf"}
            )

        supabase.table("compilazioni").update({
            "dati_json":  json.dumps(dati, ensure_ascii=False),
            "modificato": True,
        }).eq("id", rid).execute()

        return None
    except Exception as e:
        return str(e)


def lista_compilazioni():
    try:
        res = supabase.table("compilazioni") \
            .select("*") \
            .order("data_ora", desc=True) \
            .execute()
        return res.data
    except Exception as e:
        print(f"Errore lista: {e}")
        return []


def get_pdf(percorso: str, nome_file: str):
    try:
        path = f"{percorso}/{nome_file}"
        return supabase.storage.from_(config.SUPABASE_BUCKET).download(path)
    except Exception:
        return None


def get_allegato(path: str):
    try:
        return supabase.storage.from_(config.SUPABASE_BUCKET).download(path)
    except Exception:
        return None


def elimina_compilazione(rid: int, percorso: str):
    try:
        # Elimina tutti i file dal bucket
        files = supabase.storage.from_(config.SUPABASE_BUCKET).list(percorso)
        if files:
            paths = [f"{percorso}/{f['name']}" for f in files]
            supabase.storage.from_(config.SUPABASE_BUCKET).remove(paths)
        # Elimina la riga dal database
        supabase.table("compilazioni").delete().eq("id", rid).execute()
        return None
    except Exception as e:
        return str(e)
