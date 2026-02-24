import os
import json
import time
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

# Configurações via ambiente
CKAN_BASE_URL = os.environ.get("CKAN_BASE_URL", "https://dadosabertos.ifmg.edu.br")
CKAN_OUTPUT_DIR = os.environ.get("CKAN_OUTPUT_DIR", "dados_ifmg_ckan")
CKAN_HTTP_TIMEOUT = int(os.environ.get("CKAN_HTTP_TIMEOUT", "60"))
CKAN_DOWNLOAD_TIMEOUT = int(os.environ.get("CKAN_DOWNLOAD_TIMEOUT", "120"))
CKAN_RETRIES = int(os.environ.get("CKAN_RETRIES", "3"))
CKAN_BACKOFF_BASE = float(os.environ.get("CKAN_BACKOFF_BASE", "2.0"))


def sanitize_filename(name: str) -> str:
    invalid = '[]:*?/\\\n\r\t'  # caracteres ruins em nomes
    clean = ''.join(c for c in (name or "") if c not in invalid).strip()
    return clean.replace(" ", "_") or "arquivo"


def get_with_retries(url: str, *, stream: bool = False, timeout: int = CKAN_HTTP_TIMEOUT,
                      retries: int = CKAN_RETRIES, backoff_base: float = CKAN_BACKOFF_BASE) -> requests.Response:
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, stream=stream, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            last_err = e
            if attempt < retries:
                sleep_s = min(backoff_base ** attempt, 30.0)
                time.sleep(sleep_s)
            else:
                break
    raise last_err


def save_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def download_resource(resource: dict, target_dir: str) -> dict:
    url = resource.get("url")
    name = resource.get("name") or ""
    fmt = resource.get("format") or ""
    status = {
        "id": resource.get("id"),
        "name": name,
        "url": url,
        "saved_path": None,
        "ok": False,
        "error": None,
    }
    if not url:
        status["error"] = "Sem URL"
        return status
    # Deriva nome do arquivo a partir da URL ou nome do recurso
    parsed = urlparse(url)
    basename = os.path.basename(parsed.path) or sanitize_filename(name)
    if not os.path.splitext(basename)[1] and fmt:
        # adiciona extensão do formato quando ausente
        basename = f"{basename}.{fmt.lower()}"
    fname = sanitize_filename(basename)
    out_path = os.path.join(target_dir, fname)
    os.makedirs(target_dir, exist_ok=True)
    try:
        resp = get_with_retries(url, stream=True, timeout=CKAN_DOWNLOAD_TIMEOUT)
        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        status["saved_path"] = out_path
        status["ok"] = True
    except requests.exceptions.RequestException as e:
        status["error"] = str(e)
    return status


def main():
    print(f"Iniciando download do CKAN em: {CKAN_BASE_URL}")
    os.makedirs(CKAN_OUTPUT_DIR, exist_ok=True)

    # Lista de datasets
    pkg_list_url = f"{CKAN_BASE_URL}/api/action/package_list"
    try:
        print(f"Buscando lista de datasets: {pkg_list_url}")
        resp = get_with_retries(pkg_list_url, timeout=CKAN_HTTP_TIMEOUT)
        dataset_ids = resp.json().get("result", [])
        print(f"Encontrados {len(dataset_ids)} datasets.")
    except Exception as e:
        print(f"Erro ao obter lista de datasets: {e}")
        return

    for ds_id in dataset_ids:
        print(f"\n--- Processando dataset: {ds_id} ---")
        show_url = f"{CKAN_BASE_URL}/api/action/package_show?id={ds_id}"
        ds_dir = os.path.join(CKAN_OUTPUT_DIR, ds_id)
        res_dir = os.path.join(ds_dir, "resources")
        os.makedirs(ds_dir, exist_ok=True)
        # Metadados via API
        try:
            r = get_with_retries(show_url, timeout=CKAN_HTTP_TIMEOUT)
            result = r.json().get("result", {})
            save_json(os.path.join(ds_dir, "metadata.json"), result)
            resources = result.get("resources", [])
        except Exception as e:
            print(f"Erro ao obter metadata: {e}")
            resources = []
        # Download de recursos
        statuses = []
        if not resources:
            print("Sem recursos para este dataset.")
        for resource in resources:
            st = download_resource(resource, res_dir)
            statuses.append(st)
            if st["ok"]:
                print(f"✔ Baixado: {st['saved_path']}")
            else:
                print(f"✖ Falha: {resource.get('url')} — {st['error']}")
        # Salva status de recursos
        save_json(os.path.join(ds_dir, "resource_status.json"), {"dataset": ds_id, "resources": statuses})

    print("\nConcluído. Dados salvos em:", CKAN_OUTPUT_DIR)


if __name__ == "__main__":
    main()