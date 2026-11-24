"""
Agente Praktix: ideas y borradores de publicaciones para Instagram -> Telegram.

Uso:
    python praktix_agente.py --kit            # una sola vez: kit de lanzamiento (8 primeras publicaciones)
    python praktix_agente.py --semana         # 2 borradores: 1 caso + 1 educativa (para correr 2 veces por semana)
    python praktix_agente.py --tips           # 3 tips de IA para todo publico (para correr 1 vez por semana)
    python praktix_agente.py --tips --n=5     # cantidad de tips distinta
    Agrega --seco para imprimir en pantalla en vez de enviar a Telegram.

Variables de entorno: GEMINI_API_KEY, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
Archivos: casos.json (tus casos, la unica fuente de hechos), historial.json (lo ya propuesto)

IMPORTANTE sobre los tips: son SUGERENCIAS que genera la IA, no hechos tuyos. Cada tip llega con una
lista "para probar tu" y "datos por verificar". Pruebalo tu antes de publicar.
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
TIPS_POR_SEMANA = 3

BIO = (
    "Automatizo con IA lo que antes tomaba días.\n"
    "740 informes · 500+ correos personalizados.\n"
    "Casos reales, paso a paso ↓"
)

# Temas educativos: cada uno parte de la vida diaria, no de la tecnologia.
TEMAS_EDUCATIVOS = [
    "Automatizar es como tener un ayudante que hace por ti lo repetitivo (y lo que NO es)",
    "Tres tareas de oficina aburridas que se pueden dejar en manos de la IA sin saber programar",
    "Por que la IA a veces se equivoca con total seguridad y como revisar lo que te entrega",
    "Como pedirle las cosas a una IA para que te entienda: 3 reglas que sirven siempre",
    "Como se hablan dos aplicaciones entre si: la historia del mesero que lleva tu pedido a la cocina",
    "Una hoja de calculo que trabaja sola: para que sirve y cuando te cambia la semana",
    "Cuando conviene automatizar una tarea y cuando es mejor seguir haciendola a mano",
    "Como cuidar los datos de otras personas cuando usas IA en el trabajo (lo que nunca debes pegarle)",
    "Chat de IA vs asistente que hace tareas por ti: la diferencia explicada con un ejemplo de tienda",
    "Cinco errores comunes de quien empieza a automatizar y como evitarlos",
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

# Categorias de tips: cada una apunta a un publico distinto. Se rotan para variar.
CATEGORIAS_TIPS = [
    "Para el dia a dia en casa: comidas, compras, listas, organizacion del hogar",
    "Para estudiantes y para quien quiere aprender algo nuevo",
    "Para quien trabaja en oficina: correos, resumenes, actas, reuniones",
    "Para emprendedores y negocios pequenos: mensajes a clientes, ideas de publicaciones, respuestas a preguntas frecuentes",
    "Para mamas y papas: actividades, rutinas, tareas del colegio (sin que la IA haga la tarea por el nino)",
    "Para adultos mayores y para quien apenas se inicia: perderle el miedo, primeros pasos, pedir ayuda sencilla",
    "Para escribir mejor: cartas, mensajes dificiles, hojas de vida, agradecimientos",
    "Para entender documentos: facturas, manuales, cartas largas, explicados en palabras sencillas",
    "Para planear: viajes, eventos, presupuesto familiar, agenda de la semana",
    "Para aprender idiomas y traducir mensajes cotidianos",
    "Para ser creativo: ideas de regalos, nombres, celebraciones, decoracion",
    "Para tomar decisiones: comparar opciones, pros y contras, preguntas que conviene hacerse",
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

REGLAS_LENGUAJE = """LENGUAJE SENCILLO (el publico NO sabe de tecnologia: senoras, estudiantes, duenos de tienda, jubilados):
- Escribe como si le explicaras a un vecino o a tu mama. Frases cortas (maximo 18 palabras). Una sola idea por pantalla.
- Empieza SIEMPRE por una situacion de la vida diaria (cocina, familia, colegio, tienda, oficina, el celular) y despues conecta con la IA.
- Palabras prohibidas si no las explicas con una comparacion cotidiana: API, script, prompt, token, algoritmo, modelo, LLM,
  flujo, integracion, base de datos, JSON, codigo, backend, scraping, pipeline, framework, endpoint, parametro.
  Si de verdad hace falta una, usa primero la comparacion y deja la palabra tecnica al final, entre parentesis.
- En vez de 'prompt' di 'la instruccion que le escribes'. En vez de 'agente' di 'asistente que hace tareas por ti'.
  En vez de 'automatizar un flujo' di 'dejar que la computadora haga sola los pasos repetitivos'.
- Usa ejemplos concretos y reconocibles (un recibo, el mercado, el grupo de WhatsApp, una agenda), no abstracciones.
- Cada pantalla debe entenderse aunque la persona no haya visto las demas.
- Verbos de accion y tono amable, nunca de profesor ni de experto que mira desde arriba.
"""

REGLAS_TIPS = """REGLAS PARA TIPS DE IA (son consejos generales, NO casos propios):
- Un tip NO es algo que la cuenta hizo. Nunca digas "yo lo hice", "me funciono" ni "mis clientes lo usan". Usa "puedes", "prueba", "te sirve para".
- No inventes cifras, estudios, porcentajes ni promesas de tiempo ahorrado. No digas "en 5 minutos" ni "ahorra horas".
- Debe funcionar con cualquier asistente de IA gratuito de conversacion (ChatGPT, Claude, Gemini, Copilot...). No dependas de una funcion
  de pago ni de un boton especifico de una sola app. Si mencionas una herramienta o funcion concreta, anotala en "datos_a_verificar".
- La instruccion de ejemplo debe poder copiarse y pegarse tal cual, con huecos entre [corchetes] para que la persona ponga lo suyo.
- Privacidad: nunca pongas datos personales reales en los ejemplos. Incluye siempre en "cuidado" que no se peguen cedulas, claves,
  historias clinicas, numeros de cuenta ni datos de clientes o de otras personas.
- Salud, dinero y temas legales: solo como ayuda para ORGANIZAR preguntas o ENTENDER un texto con palabras sencillas, nunca para
  diagnosticar, recetar, invertir ni dar asesoria legal. Recomienda confirmar con un profesional.
- Recuerda siempre que la IA puede equivocarse: el tip debe incluir como verificar el resultado ("como_verificar").
- Un tip debe poder hacerse en 3 a 5 pasos, por alguien que nunca ha usado IA mas que para consultar.
"""


# ---------------------------------------------------------------------------
# Gemini y Telegram
# ---------------------------------------------------------------------------

def llamar_gemini(prompt: str, como_json: bool = True, temperatura: float = 0.6):
    from google import genai
    from google.genai import types

    cliente = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    config = types.GenerateContentConfig(
        response_mime_type="application/json" if como_json else "text/plain",
        temperature=temperatura,
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


def elegir_categorias_tips(historial: dict, n: int) -> list[str]:
    """Las n categorias menos usadas (en empate, las que llevan mas tiempo sin salir), todas distintas."""
    usos = {c: 0 for c in CATEGORIAS_TIPS}
    ultimo = {c: -1 for c in CATEGORIAS_TIPS}
    for i, p in enumerate(historial["publicados"]):
        if p.get("tipo") == "tip" and p.get("categoria") in usos:
            usos[p["categoria"]] += 1
            ultimo[p["categoria"]] = i
    ordenadas = sorted(CATEGORIAS_TIPS, key=lambda c: (usos[c], ultimo[c]))
    return ordenadas[:max(1, min(n, len(ordenadas)))]


def ganchos_previos(historial: dict, n: int = 12) -> list[str]:
    return [p["gancho"] for p in historial["publicados"] if p.get("gancho")][-n:]


def titulos_tips_previos(historial: dict, n: int = 40) -> list[str]:
    return [p["titulo"] for p in historial["publicados"] if p.get("tipo") == "tip" and p.get("titulo")][-n:]


# ---------------------------------------------------------------------------
# Escritor y revisor (casos y educativas)
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

COMO ENSEÑAR ESTE TEMA:
- Pantalla 1: una situacion cotidiana que cualquiera reconozca (sin mencionar tecnologia todavia).
- Pantallas siguientes: la idea explicada con una comparacion de la vida diaria (cocina, tienda, familia, colegio...).
- Pantalla final: que puede hacer la persona HOY, en una sola accion pequena.
- Si el tema suena tecnico, tu trabajo es traducirlo: nadie debe necesitar buscar una palabra en Google para entenderte.

Conecta la idea con alguno de estos casos reales solo como ejemplo breve, sin inventar datos:
{json.dumps([{k: c[k] for k in ("titulo", "solucion", "herramientas")} for c in cargar_casos()], ensure_ascii=False)}"""
    return llamar_gemini(f"""Eres redactora de la cuenta de Instagram Praktix ("Inteligencia aplicada"), de una
profesional que automatiza tareas con IA y quiere mostrar su trabajo a posibles clientes.
{base}

Evita repetir estos ganchos ya usados: {previos}

{REGLAS}
{REGLAS_LENGUAJE}
{FORMATO_BORRADOR}""")


def revisar(borrador: dict, tipo: str, caso: dict | None) -> dict:
    hechos = json.dumps(caso, ensure_ascii=False, indent=2) if caso else "(publicacion educativa: no debe afirmar cifras ni resultados propios)"
    return llamar_gemini(f"""Eres revisora de contenido. Revisa el borrador contra las reglas y los hechos.
Busca: cifras no confirmadas, datos inventados, nombres reales, afirmaciones de revision profesional sin respaldo,
promesas de resultados, exageraciones.
Busca TAMBIEN lenguaje tecnico: palabras de la lista prohibida sin explicar, frases largas, pantallas que no se
entienden solas, explicaciones que empiezan por la tecnologia en vez de por la vida diaria. Reescribelas en palabras sencillas.

HECHOS PERMITIDOS:
{hechos}

{REGLAS}
{REGLAS_LENGUAJE}

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
# Tips de IA para todo publico
# ---------------------------------------------------------------------------

FORMATO_TIP = """Devuelve SOLO un objeto JSON con estas claves:
- "tip": un objeto con:
    - "titulo": nombre corto y claro del tip (maximo 10 palabras, sin tecnicismos)
    - "para_quien": a quien le sirve, en una frase
    - "problema": la situacion cotidiana que resuelve, contada en 1-2 frases
    - "pasos": lista de 3 a 5 pasos muy concretos, en lenguaje sencillo
    - "instruccion_ejemplo": el texto exacto que la persona puede copiar y pegar en cualquier asistente de IA, con [huecos] para completar
    - "como_verificar": como comprobar que lo que respondio la IA esta bien (1-2 frases)
    - "cuidado": que NO hacer o que cuidar (privacidad, errores de la IA, limites)
- "para_probar": lista de 3 a 5 cosas concretas que la duena de la cuenta debe probar ella misma antes de publicar
  (por ejemplo: "Pega la instruccion en un asistente y mira si la respuesta sirve", "Prueba con un caso real tuyo sin datos personales")
- "datos_a_verificar": lista de afirmaciones sobre herramientas, funciones, precios o limites que podrian haber cambiado y hay que confirmar (vacia si no hay)
- "dificultad": "facil" o "medio"
- "formato": "carrusel" o "reel"
- "gancho": primera linea que detiene el scroll (maximo 12 palabras, empieza por el problema, no por la tecnologia)
- "pantallas": lista de 6 a 8 textos cortos: 1 problema cotidiano, 3 a 5 pasos, 1 con la instruccion lista para copiar, 1 de cuidado/cierre
- "pie": texto de la publicacion (maximo 600 caracteres), termina invitando a guardar o a contar si lo probaron
- "hashtags": lista de 5 hashtags en espanol
- "que_mostrar": que captura o imagen usar, sin datos reales de nadie
"""


def escribir_tip(categoria: str, previos: list[str], titulos_previos: list[str]) -> dict:
    return llamar_gemini(f"""Eres redactora de la cuenta de Instagram Praktix ("Inteligencia aplicada"). La cuenta quiere ensenar
a TODO tipo de publico a sacarle provecho a la IA en su dia a dia. Mucha gente aun no la usa, o solo la usa para consultar datos.
Tu trabajo es proponer UN tip practico y facil de aplicar, que le cambie la rutina a alguien que nunca ha usado IA para otra cosa.

CATEGORIA / PUBLICO DE ESTE TIP: {categoria}

Debe ser algo que la duena de la cuenta pueda probar ella misma en pocos minutos, antes de publicarlo.
No repitas estos tips ya propuestos: {titulos_previos}
Evita repetir estos ganchos: {previos}

{REGLAS_TIPS}
{REGLAS_LENGUAJE}
{FORMATO_TIP}""", temperatura=0.7)


def revisar_tip(borrador: dict) -> dict:
    return llamar_gemini(f"""Eres revisora de contenido. Revisa este tip de IA para Instagram contra las reglas.
Busca: tecnicismos sin explicar, frases largas, promesas de tiempo o resultados, cifras o estudios inventados,
afirmaciones de que la cuenta ya lo uso o le funciono, consejos medicos/legales/financieros directos, ejemplos con datos
personales reales, pasos que dependan de una funcion de pago o de una app concreta sin avisar, pasos confusos o imposibles
de hacer para alguien que nunca ha usado IA, y falta de como verificar o de cuidado.
Corrige todo lo que encuentres.

{REGLAS_TIPS}
{REGLAS_LENGUAJE}

BORRADOR:
{json.dumps(borrador, ensure_ascii=False, indent=2)}

Devuelve SOLO un objeto JSON:
- "aprobado": true si no hay problemas, false si los hay
- "problemas": lista de problemas encontrados (vacia si no hay)
- "borrador_corregido": el borrador completo con exactamente las mismas claves y los problemas corregidos (si estaba bien, el mismo)
""", temperatura=0.4)


def producir_tip(categoria: str, previos: list[str], titulos_previos: list[str]) -> tuple[dict, list[str]]:
    b = escribir_tip(categoria, previos, titulos_previos)
    rev = revisar_tip(b)
    final = rev.get("borrador_corregido") or b
    return final, rev.get("problemas", [])


def formatear_tip(numero: int, total: int, categoria: str, b: dict, problemas: list[str]) -> str:
    tip = b.get("tip", {}) or {}
    pasos = "\n".join(f"  {i}. {p}" for i, p in enumerate(tip.get("pasos", []), 1))
    pantallas = "\n".join(f"  {i}. {t}" for i, t in enumerate(b.get("pantallas", []), 1))
    para_probar = "\n".join(f"  [ ] {x}" for x in b.get("para_probar", []))
    por_verificar = "\n".join(f"  - {x}" for x in b.get("datos_a_verificar", []))

    texto = (
        f"PRAKTIX · TIP {numero} de {total}: {tip.get('titulo', '')}\n"
        f"Publico: {categoria}\n"
        f"Dificultad: {b.get('dificultad', '')} · Formato sugerido: {b.get('formato', '')}\n\n"
        f"PARA QUIEN: {tip.get('para_quien', '')}\n"
        f"EL PROBLEMA: {tip.get('problema', '')}\n\n"
        f"PASOS:\n{pasos}\n\n"
        f"INSTRUCCION PARA COPIAR Y PEGAR:\n{tip.get('instruccion_ejemplo', '')}\n\n"
        f"COMO REVISAR LO QUE RESPONDA: {tip.get('como_verificar', '')}\n"
        f"CUIDADO: {tip.get('cuidado', '')}\n"
        f"\n--- BORRADOR DE LA PUBLICACION ---\n"
        f"Gancho: {b.get('gancho', '')}\n\n"
        f"Pantallas:\n{pantallas}\n\n"
        f"Texto de la publicacion:\n{b.get('pie', '')}\n\n"
        f"Hashtags: {' '.join(b.get('hashtags', []))}\n\n"
        f"Que mostrar: {b.get('que_mostrar', '')}\n"
        f"\n--- ANTES DE PUBLICAR, PRUEBALO TU ---\n{para_probar}"
    )
    if por_verificar:
        texto += f"\n\nDATOS POR VERIFICAR (pueden haber cambiado):\n{por_verificar}"
    if problemas:
        texto += "\n\nLa revisora corrigio: " + "; ".join(problemas)
    texto += (
        "\n\nESTADO: sin probar. Este tip lo propuso la IA; no lo publiques hasta que lo hayas practicado "
        "y confirmado que funciona. Revisa tambien que no se cuele ningun dato real."
    )
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


def modo_tips(seco: bool, n: int = TIPS_POR_SEMANA) -> None:
    hist = cargar_historial()
    previos = ganchos_previos(hist)
    titulos = titulos_tips_previos(hist)
    hoy = datetime.now().strftime("%Y-%m-%d")
    categorias = elegir_categorias_tips(hist, n)
    total = len(categorias)

    entregar(
        f"PRAKTIX · Tips de IA de la semana ({hoy})\n"
        f"Te llegan {total} tips. Son propuestas de la IA: pruebalos tu y publica solo los que te funcionen.",
        seco,
    )

    for i, categoria in enumerate(categorias, 1):
        borrador, problemas = producir_tip(categoria, previos, titulos)
        entregar(formatear_tip(i, total, categoria, borrador, problemas), seco)

        tip = borrador.get("tip", {}) or {}
        titulo = tip.get("titulo", "")
        gancho = borrador.get("gancho", "")
        hist["publicados"].append({
            "fecha": hoy, "tipo": "tip", "categoria": categoria, "titulo": titulo,
            "gancho": gancho, "estado": "por_probar",
        })
        previos.append(gancho)
        titulos.append(titulo)
        if not seco:
            guardar_historial(hist)  # se guarda tip a tip: si uno falla, no se pierde lo anterior


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
{REGLAS_LENGUAJE}

Devuelve SOLO un objeto JSON con:
- "publicaciones": lista de 8 objetos con "numero", "semana", "tipo", "titulo", "formato", "gancho", "idea" (2 lineas), "que_mostrar"
- "historias": lista de 4 textos cortos de historias para la primera semana
""")
    lineas = ["PRAKTIX · Kit de lanzamiento", "", "Bio elegida:", BIO, "",
              "Nombre del perfil: Praktix | IA y automatización",
              "Destacadas: Casos · Cómo lo hago · Herramientas · Tips de IA · Contacto", "", "Plan de 2 semanas:"]
    for p in plan.get("publicaciones", []):
        lineas.append(
            f"\n{p.get('numero')}. (semana {p.get('semana')}, {p.get('tipo')}, {p.get('formato')}) {p.get('titulo')}\n"
            f"   Gancho: {p.get('gancho')}\n   Idea: {p.get('idea')}\n   Mostrar: {p.get('que_mostrar')}"
        )
    lineas.append("\nHistorias de la primera semana:")
    lineas += [f"  - {h}" for h in plan.get("historias", [])]
    lineas.append("\nAntes de publicar: revisa que ninguna imagen o texto tenga datos reales, y completa lo marcado [CONFIRMAR].")
    entregar("\n".join(lineas), seco)


def leer_n(args: list[str]) -> int:
    for a in args:
        if a.startswith("--n="):
            try:
                return max(1, min(int(a.split("=", 1)[1]), len(CATEGORIAS_TIPS)))
            except ValueError:
                pass
    return TIPS_POR_SEMANA


def main() -> None:
    lista = sys.argv[1:]
    args = set(lista)
    seco = "--seco" in args
    try:
        if "--kit" in args:
            modo_kit(seco)
        elif "--semana" in args:
            modo_semana(seco)
        elif "--tips" in args:
            modo_tips(seco, leer_n(lista))
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
