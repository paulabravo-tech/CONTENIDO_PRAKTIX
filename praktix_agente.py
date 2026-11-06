"""
Agente Praktix: ideas y borradores de publicaciones para Instagram -> Telegram.

Uso:
    python praktix_agente.py --kit        # una sola vez: kit de lanzamiento (8 primeras publicaciones)
    python praktix_agente.py --semana     # 2 borradores: 1 caso + 1 educativa (para correr 2 veces por semana)
    Agrega --seco para imprimir en pantalla en vez de enviar a Telegram.

Variables de entorno: GEMINI_API_KEY, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
Archivos: casos.json (tus casos, la unica fuente de hechos), historial.json (lo ya propuesto)
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

AQUI = Path(__file__).parent
MODELO = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
MODELOS_RESPALDO = ["gemini-3.6-flash"]
ESPERAS_REINTENTO = [10, 30, 60]

BIO = (
    "Automatizo con IA lo que antes tomaba días.\n"
    "740 informes · 500+ correos personalizados.\n"
    "Casos reales, paso a paso ↓"
)

TEMAS_EDUCATIVOS = [
    "Qué es automatizar y qué NO es (con un ejemplo cotidiano)",
    "Tres tareas de oficina que una persona puede automatizar sin saber programar",
    "Por qué la IA se equivoca y cómo revisar lo que te entrega",
    "Cómo pedirle algo a una IA para que te sirva: instrucciones claras en 3 pasos",
    "Qué es una API explicado con la metáfora de un mesero",
    "Qué es una hoja de cálculo conectada a un script, y para qué sirve",
    "Cuándo conviene automatizar y cuándo es mejor hacerlo a mano",
    "Cómo proteger los datos de otras personas cuando usas IA en el trabajo",
    "Qué hace un 'agente' de IA y en qué se diferencia de un chat",
    "Cinco errores comunes al empezar con automatización",
]

ANGULOS = [
    "Historia: cuenta el problema como una situacion cotidiana que el publico reconozca, y luego la solucion.",
    "Paso a paso: explica como funciona en 4 pasos simples.",
    "Leccion aprendida: algo que se ajusto o se probo hasta que funciono.",
    "Mito contra realidad: un mito comun sobre la automatizacion o la IA que este caso desmiente.",
    "Pregunta al publico: una situacion que le pase a su negocio y como este caso se parece.",
    "Herramientas: que se uso y para que, explicado sin tecnicismos.",
    "Detras de camaras: como se probo y reviso antes de usarlo de verdad.",
    "Invitacion: que podria hacer algo parecido por el negocio de quien lee, con llamado claro a escribirte.",
]

REGLAS = """REGLAS OBLIGATORIAS (privacidad y honestidad):
- Los unicos hechos permitidos son los del caso entregado. No inventes cifras, clientes, plazos, porcentajes ni resultados.
- Las cifras en "cifras_por_confirmar" NO se pueden afirmar. Si hacen falta, escribe [CONFIRMAR: ...] en su lugar.
- Nunca menciones nombres de instituciones, municipios, convenios, entidades contratantes ni personas reales.
- Un ejemplo hipotetico para otro negocio solo se permite si empieza con 'Ejemplo:' y no usa datos reales.
- Respeta la lista "no_afirmar" del caso: lo que alli aparece no se puede decir.
- Nunca menciones presupuestos, tarifas, pagos, montos ni porcentajes de ahorro. No digas que un tiempo se redujo si no hay medicion.
- Nunca afirmes que hubo revision profesional o humana salvo que este en los hechos confirmados.
- No prometas resultados a quien lea; cuenta lo que se hizo.
- Espanol colombiano claro, tuteo, sin tecnicismos innecesarios, sin exageraciones ni frases tipo "revoluciona".
- La cuenta es de una sola persona (primera persona singular, femenino: "automaticé", "creé").
"""


# ---------------------------------------------------------------------------
# Gemini y Telegram
# ---------------------------------------------------------------------------

def llamar_gemini(prompt: str, como_json: bool = True):
    from google import genai
    from google.genai import types

    cliente = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    config = types.GenerateContentConfig(
        response_mime_type="application/json" if como_json else "text/plain",
        temperature=0.6,
    )
    modelos = [MODELO] + [m for m in MODELOS_RESPALDO if m != MODELO]
    ultimo = None
    for modelo in modelos:
        for intento, espera in enumerate(ESPERAS_REINTENTO + [None], 1):
            try:
                r = cliente.models.generate_content(model=modelo, contents=prompt, config=config)
                return json.loads(r.text) if como_json else r.text
            except Exception as e:  # noqa: BLE001
                codigo = getattr(e, "code", None) or getattr(e, "status_code", None)
                ultimo = e
                print(f"[aviso] {modelo}, intento {intento}: {type(e).__name__} {codigo}")
                if codigo == 404:
                    break
                if codigo not in (429, 500, 502, 503, 504):
                    raise
                if espera is None:
                    break
                time.sleep(espera)
    raise RuntimeError(f"Gemini no respondio con ningun modelo: {ultimo}")


def enviar_telegram(texto: str) -> None:
    token = os.environ["TELEGRAM_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # Texto plano (sin HTML) para que ningun caracter rompa el envio; se parte en trozos de 4000.
    for i in range(0, len(texto), 4000):
        r = requests.post(url, json={"chat_id": chat_id, "text": texto[i:i + 4000]}, timeout=30)
        if not r.ok:
            raise RuntimeError(f"Telegram respondio {r.status_code}: {r.text}")


def entregar(texto: str, seco: bool) -> None:
    if seco:
        print(texto)
    else:
        enviar_telegram(texto)


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------

def cargar_casos() -> list[dict]:
    return json.loads((AQUI / "casos.json").read_text(encoding="utf-8"))


def cargar_historial() -> dict:
    p = AQUI / "historial.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"publicados": []}


def guardar_historial(h: dict) -> None:
    (AQUI / "historial.json").write_text(json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8")


def elegir_caso(casos: list[dict], historial: dict) -> dict:
    """El caso menos usado hasta ahora; en empate, el que lleva mas tiempo sin salir."""
    usos = {c["id"]: 0 for c in casos}
    ultimo = {c["id"]: -1 for c in casos}
    for n, p in enumerate(historial["publicados"]):
        if p.get("caso_id") in usos:
            usos[p["caso_id"]] += 1
            ultimo[p["caso_id"]] = n
    return min(casos, key=lambda c: (usos[c["id"]], ultimo[c["id"]]))


def elegir_angulo(caso: dict, historial: dict) -> str:
    """Rota los angulos por caso: cada vez que sale el caso, toca el siguiente angulo."""
    veces = sum(1 for p in historial["publicados"] if p.get("caso_id") == caso["id"])
    return ANGULOS[veces % len(ANGULOS)]


def elegir_tema(historial: dict) -> str:
    usados = [p.get("tema") for p in historial["publicados"] if p.get("tipo") == "educativa"]
    for t in TEMAS_EDUCATIVOS:
        if t not in usados:
            return t
    return TEMAS_EDUCATIVOS[len(usados) % len(TEMAS_EDUCATIVOS)]


def ganchos_previos(historial: dict, n: int = 12) -> list[str]:
    return [p["gancho"] for p in historial["publicados"] if p.get("gancho")][-n:]


# ---------------------------------------------------------------------------
# Escritor y revisor
# ---------------------------------------------------------------------------

FORMATO_BORRADOR = """Devuelve SOLO un objeto JSON con estas claves:
- "formato": "carrusel" o "reel"
- "gancho": la primera linea que detiene el scroll (maximo 12 palabras)
- "pantallas": lista de 5 a 8 textos cortos, uno por pantalla del carrusel (o por escena del reel)
- "pie": texto de la publicacion (maximo 600 caracteres), terminando con una pregunta o invitacion a guardar/escribir
- "hashtags": lista de 5 hashtags en espanol
- "que_mostrar": que imagen o captura usar, recordando que no se muestran datos reales
"""


def escribir(tipo: str, caso: dict | None, tema: str | None, previos: list[str], angulo: str | None = None) -> dict:
    if tipo == "caso":
        base = f"""Escribe el borrador de una publicacion de Instagram que cuenta este caso real:
{json.dumps(caso, ensure_ascii=False, indent=2)}

ANGULO DE ESTA PUBLICACION (el caso ya se ha contado antes desde otros angulos; usa solo este): {angulo}"""
    else:
        base = f"""Escribe el borrador de una publicacion EDUCATIVA de Instagram sobre este tema: "{tema}".
Conecta la idea con alguno de estos casos reales solo como ejemplo breve, sin inventar datos:
{json.dumps([{k: c[k] for k in ("titulo", "solucion", "herramientas")} for c in cargar_casos()], ensure_ascii=False)}"""
    return llamar_gemini(f"""Eres redactora de la cuenta de Instagram Praktix ("Inteligencia aplicada"), de una
profesional que automatiza tareas con IA y quiere mostrar su trabajo a posibles clientes.
{base}

Evita repetir estos ganchos ya usados: {previos}

{REGLAS}
{FORMATO_BORRADOR}""")


def revisar(borrador: dict, tipo: str, caso: dict | None) -> dict:
    hechos = json.dumps(caso, ensure_ascii=False, indent=2) if caso else "(publicacion educativa: no debe afirmar cifras ni resultados propios)"
    return llamar_gemini(f"""Eres revisora de contenido. Revisa el borrador contra las reglas y los hechos.
Busca: cifras no confirmadas, datos inventados, nombres reales, afirmaciones de revision profesional sin respaldo,
promesas de resultados, exageraciones.

HECHOS PERMITIDOS:
{hechos}

{REGLAS}

BORRADOR:
{json.dumps(borrador, ensure_ascii=False, indent=2)}

Devuelve SOLO un objeto JSON:
- "aprobado": true si no hay problemas, false si los hay
- "problemas": lista de problemas encontrados (vacia si no hay)
- "borrador_corregido": el borrador completo con el mismo formato y los problemas corregidos (si estaba bien, el mismo)
""")


def producir(tipo: str, caso: dict | None, tema: str | None, previos: list[str], angulo: str | None = None) -> tuple[dict, list[str]]:
    b = escribir(tipo, caso, tema, previos, angulo)
    rev = revisar(b, tipo, caso)
    final = rev.get("borrador_corregido") or b
    return final, rev.get("problemas", [])


def formatear(titulo: str, b: dict, problemas: list[str]) -> str:
    pantallas = "\n".join(f"  {i}. {t}" for i, t in enumerate(b.get("pantallas", []), 1))
    texto = (
        f"{titulo}\n"
        f"Formato: {b.get('formato', '')}\n\n"
        f"Gancho: {b.get('gancho', '')}\n\n"
        f"Pantallas:\n{pantallas}\n\n"
        f"Texto de la publicacion:\n{b.get('pie', '')}\n\n"
        f"Hashtags: {' '.join(b.get('hashtags', []))}\n\n"
        f"Que mostrar: {b.get('que_mostrar', '')}"
    )
    if problemas:
        texto += "\n\nLa revisora corrigio: " + "; ".join(problemas)
    if "[CONFIRMAR" in texto:
        texto += "\n\nOJO: hay datos marcados [CONFIRMAR]. Completalos o quitalos antes de publicar."
    texto += "\n\nRevisa que no se cuele ningun dato real antes de publicar."
    return texto


# ---------------------------------------------------------------------------
# Modos
# ---------------------------------------------------------------------------

def modo_semana(seco: bool) -> None:
    casos, hist = cargar_casos(), cargar_historial()
    previos = ganchos_previos(hist)
    hoy = datetime.now().strftime("%Y-%m-%d")

    caso = elegir_caso(casos, hist)
    angulo = elegir_angulo(caso, hist)
    b1, p1 = producir("caso", caso, None, previos, angulo)
    entregar(formatear(f"PRAKTIX · Borrador 1 (caso): {caso['titulo']}\nAngulo: {angulo.split(':')[0]}", b1, p1), seco)
    hist["publicados"].append({"fecha": hoy, "tipo": "caso", "caso_id": caso["id"], "angulo": angulo.split(":")[0], "gancho": b1.get("gancho", "")})

    tema = elegir_tema(hist)
    b2, p2 = producir("educativa", None, tema, previos + [b1.get("gancho", "")])
    entregar(formatear(f"PRAKTIX · Borrador 2 (educativa): {tema}", b2, p2), seco)
    hist["publicados"].append({"fecha": hoy, "tipo": "educativa", "tema": tema, "gancho": b2.get("gancho", "")})

    if not seco:
        guardar_historial(hist)


def modo_kit(seco: bool) -> None:
    casos = cargar_casos()
    plan = llamar_gemini(f"""Eres estratega de contenido. Prepara el plan de las 8 primeras publicaciones de Instagram de Praktix
("Inteligencia aplicada"): una profesional que automatiza con IA y quiere atraer clientes mostrando sus casos reales.
Debe haber: 1 presentacion de quien es y que hace, 4 publicaciones de casos (uno por caso, en este orden de preferencia:
agente de noticias, formulario con script, correos, informes), 2 educativas y 1 'detras de camaras' sobre como se trabaja.
Ordena para 2 semanas, 2 publicaciones por semana mas 4 historias.

CASOS (unica fuente de hechos):
{json.dumps(casos, ensure_ascii=False, indent=2)}

{REGLAS}

Devuelve SOLO un objeto JSON con:
- "publicaciones": lista de 8 objetos con "numero", "semana", "tipo", "titulo", "formato", "gancho", "idea" (2 lineas), "que_mostrar"
- "historias": lista de 4 textos cortos de historias para la primera semana
""")
    lineas = ["PRAKTIX · Kit de lanzamiento", "", "Bio elegida:", BIO, "",
              "Nombre del perfil: Praktix | IA y automatización",
              "Destacadas: Casos · Cómo lo hago · Herramientas · Contacto", "", "Plan de 2 semanas:"]
    for p in plan.get("publicaciones", []):
        lineas.append(
            f"\n{p.get('numero')}. (semana {p.get('semana')}, {p.get('tipo')}, {p.get('formato')}) {p.get('titulo')}\n"
            f"   Gancho: {p.get('gancho')}\n   Idea: {p.get('idea')}\n   Mostrar: {p.get('que_mostrar')}"
        )
    lineas.append("\nHistorias de la primera semana:")
    lineas += [f"  - {h}" for h in plan.get("historias", [])]
    lineas.append("\nAntes de publicar: revisa que ninguna imagen o texto tenga datos reales, y completa lo marcado [CONFIRMAR].")
    entregar("\n".join(lineas), seco)


def main() -> None:
    args = set(sys.argv[1:])
    seco = "--seco" in args
    try:
        if "--kit" in args:
            modo_kit(seco)
        elif "--semana" in args:
            modo_semana(seco)
        else:
            print(__doc__)
    except Exception as e:  # noqa: BLE001
        if not seco:
            try:
                enviar_telegram(f"El agente Praktix fallo: {type(e).__name__}. Revisa la pestana Actions en GitHub.")
            except Exception:  # noqa: BLE001
                pass
        raise


if __name__ == "__main__":
    main()
