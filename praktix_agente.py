#
Agente Praktix (v2): ideas y borradores de publicaciones para Instagram -> Telegram.
Alineado con el Plan Estratégico Mes 1 (Mipymes y Project Managers: Cotizaciones, Seguimiento/Cobranza e Informes).

Uso:
    python praktix_agente.py --kit            # una sola vez: kit de lanzamiento (12 publicaciones / 4 semanas)
    python praktix_agente.py --semana         # 2 borradores: 1 caso/demo + 1 educativa (para correr 2 veces por semana)
    python praktix_agente.py --tips           # 3 tips de IA para oficina, Mipymes y Project Managers (1 vez por semana)
    python praktix_agente.py --tips --n=5     # cantidad de tips distinta
    Agrega --seco para imprimir en pantalla en vez de enviar a Telegram.

Variables de entorno: GEMINI_API_KEY, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
Archivos: casos.json (tus casos, la unica fuente de hechos), historial.json (lo ya propuesto)

IMPORTANTE sobre los tips: son SUGERENCIAS que genera la IA, no hechos tuyos. Cada tip llega con una
lista "para probar tu" y "datos por verificar". Pruebalo tu antes de publicar.


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
    "Ahorro horas operativas en Mipymes y proyectos con IA.\n"
    "Cotizaciones, seguimiento, cobros e informes en piloto automático.\n"
    "Casos reales, sin cambiar tus programas ↓"
)

# Los 3 pilares operativos definidos en Praktix_Plan_Publicaciones_y_Demos-v2
PILARES_PRAKTIX = [
    "1. Cotizaciones y Respuestas Rápidas (responder clientes y generar propuestas en segundos, CTA: COTIZAR)",
    "2. Seguimiento, Cobranza y Control de Compromisos (facturas vencidas, cotizaciones enfriadas y entregables sin perseguir gente, CTA: COBRO / PRAKTIX)",
    "3. Resúmenes Ejecutivos de Operación y Reuniones (informes semanales en Excel, actas con compromisos cumplidos y generación masiva, CTA: INFORME)",
]

PALABRAS_CLAVE_CTA = ["COTIZAR", "COBRO", "INFORME", "PRAKTIX"]

# Temas educativos: enfocados en el día a día laboral de Mipymes, oficinas y Project Managers.
TEMAS_EDUCATIVOS = [
    "De usar la IA como Google a usarla como asistente operativo en tu oficina",
    "Cómo recibir el resumen semanal de tu negocio sin pasar horas cruzando tablas en Excel",
    "Cuatro señales de que pierdes dinero y tiempo persiguiendo pendientes a mano",
    "Por qué Trello y Notion fallan cuando al equipo le da pereza actualizarlos (y cómo lograr que los compromisos se cumplan por correo)",
    "No necesitas cambiar todos tus programas para automatizar: cómo conectar el Excel y el correo que ya usas",
    "Cuánto le cuesta realmente a tu Mipyme o proyecto dedicar 25 minutos al día a perseguir pendientes",
    "Por qué la IA a veces se equivoca con total seguridad y cómo revisar sus respuestas antes de enviarlas a un cliente",
    "Cómo pedirle las cosas a una IA para que te entienda: rol, contexto y tono en 3 reglas",
    "Cómo cuidar los datos de clientes, facturas y contratos cuando usas IA en el trabajo",
    "La regla de 3 filtros para saber qué proceso de tu oficina automatizar primero",
]

ANGULOS = [
    "Historia cotidiana: cuenta el problema diario en la oficina o proyecto (cotizar lento, cobrar, armar informes) y luego la solución.",
    "Antes vs. Después: compara el tiempo y desgaste del proceso manual frente a tenerlo automatizado.",
    "Paso a paso: explica cómo funciona el sistema en 3 o 4 pasos simples, sin tecnicismos.",
    "Mito contra realidad: desmiente la idea de que automatizar requiere comprar software caro o cambiar todo lo que ya usan.",
    "Pregunta de diagnóstico: plantea una fuga de tiempo común en Mipymes o Project Managers y muestra cómo se resuelve.",
    "Detrás de cámaras: muestra cómo se probó y validó el sistema con datos ficticios antes de ponerlo a operar.",
    "Cero fricción para el equipo: destaca que nadie tiene que aprender una app nueva ni llenar tarjetitas.",
    "Invitación directa: muestra qué proceso parecido podría liberarse hoy en el negocio de quien lee, invitando a comentar la palabra clave.",
]

# Categorias de tips: reenfocadas en trabajo operativo diario (Mipymes, oficinas, equipos comerciales, administrativos y Project Managers).
CATEGORIAS_TIPS = [
    "Para dueños de Mipyme y gerentes: resumir ventas, cartera o indicadores de la semana sin sufrir con fórmulas",
    "Para equipos comerciales y contratistas: hacer seguimiento a cotizaciones enviadas sin sonar insistente",
    "Para equipos comerciales: preparar una reunión con un cliente nuevo en 2 minutos y responder objeciones de precio",
    "Para administrativos y cartera: redactar correos de cobranza preventiva o facturas vencidas con tono amable pero firme",
    "Para Project Managers y coordinadores: extraer acuerdos, responsables y fechas límite de una reunión en segundos",
    "Para Project Managers y líderes de equipo: consolidar avances dispersos de proyectos y detectar entregables en riesgo",
    "Para auxiliares administrativos y contables: limpiar y unificar tablas desordenadas para reportes en Excel",
    "Para quien trabaja con Excel a diario: pedir fórmulas exactas y cruces de datos en palabras sencillas",
    "Para atención al cliente y ventas: responder correos difíciles, reclamos o preguntas repetitivas con claridad",
    "Para cualquier oficina: transformar notas desordenadas o correos largos en un plan de acción concreto",
]

REGLAS = """REGLAS OBLIGATORIAS (privacidad, enfoque y honestidad):
- Los unicos hechos permitidos son los del caso entregado. No inventes cifras, clientes, plazos, porcentajes ni resultados.
- Las cifras en "cifras_por_confirmar" NO se pueden afirmar. Si hacen falta, escribe [CONFIRMAR: ...] en su lugar.
- Nunca menciones nombres de instituciones, municipios, convenios, entidades contratantes ni personas reales.
- Usa solo empresas ficticias si hace falta un ejemplo (ej. "Ejemplo: Suministros Andinos" o "Proyectos Alfa").
- Respeta la lista "no_afirmar" del caso: lo que alli aparece no se puede decir.
- Nunca menciones presupuestos, tarifas, pagos, montos ni porcentajes de ahorro. No digas que un tiempo se redujo si no hay medicion.
- No prometas WhatsApp automático salvo que esté explícitamente confirmado en los hechos del caso; prioriza Correo electrónico, Excel y PDF.
- No abordes temas de marketing digital, anuncios, redes sociales ni ventas de cursos; Praktix se dedica 100% a aliviar el trabajo operativo diario de oficina, Mipymes y Project Managers.
- Cierra siempre con UNA sola palabra clave de estas 4 según el tema: COTIZAR, COBRO, INFORME o PRAKTIX.
- Espanol colombiano claro, tuteo, sin tecnicismos innecesarios, sin exageraciones ni frases tipo "revoluciona".
- La cuenta es de una sola persona (primera persona singular, femenino: "automaticé", "creé", "diseñé").
"""

REGLAS_LENGUAJE = """LENGUAJE SENCILLO Y PRÁCTICO (el público son dueños de Mipyme, Project Managers, contratistas y administrativos):
- Escribe directo y claro, como una asesora práctica que entiende el día a día de una oficina. Frases cortas (maximo 18 palabras). Una sola idea por pantalla.
- Empieza SIEMPRE por una situación real del trabajo diario (cotizaciones sin responder, facturas vencidas, tablas en Excel, reuniones sin seguimiento) y después conecta con la solución.
- Palabras prohibidas si no las explicas con una comparación cotidiana: API, script, prompt, token, algoritmo, modelo, LLM,
  webhook, integración, base de datos, JSON, código, backend, scraping, pipeline, framework, endpoint, parámetro, cron.
  Si de verdad hace falta una, usa primero la comparación y deja la palabra técnica al final, entre paréntesis.
- En vez de 'prompt' di 'la instrucción que le escribes'. En vez de 'agente' di 'asistente operativo'.
  En vez de 'automatizar un flujo' di 'conectar tus herramientas para que los pasos repetitivos ocurran solos'.
- Usa ejemplos concretos de oficina (una cotización en PDF, una factura vencida, una tabla de entregables, la carpeta Borradores del correo).
- Cada pantalla debe entenderse aunque la persona no haya visto las demás.
- Tono de par profesional: cercano, resolutivo y sin aire de superioridad técnica.
"""

REGLAS_TIPS = """REGLAS PARA TIPS DE IA EN EL TRABAJO (son consejos generales, NO casos propios):
- Un tip NO es algo que la cuenta hizo. Nunca digas "yo lo hice", "me funciono" ni "mis clientes lo usan". Usa "puedes", "prueba", "te sirve para".
- Enfócate en tareas reales de oficina, Mipymes y Project Managers (correos, cotizaciones, cobranza, tablas de Excel, actas de reunión). Nada de recetas de cocina, tareas escolares ni marketing de redes.
- No inventes cifras, estudios, porcentajes ni promesas de tiempo ahorrado. No digas "en 5 minutos" ni "ahorra horas".
- Debe funcionar con cualquier asistente de IA gratuito de conversacion (ChatGPT, Claude, Gemini, Copilot...). No dependas de una funcion
  de pago ni de un boton especifico de una sola app. Si mencionas una herramienta o funcion concreta, anotala en "datos_a_verificar".
- La instruccion de ejemplo debe poder copiarse y pegarse tal cual, con huecos entre [corchetes] para que la persona ponga lo suyo.
- Privacidad: nunca pongas datos personales o confidenciales reales en los ejemplos. Incluye siempre en "cuidado" que no se peguen NITs reales, cedulas, claves, datos bancarios ni informacion confidencial de clientes o empleados.
- Temas contables, tributarios, financieros o legales: solo como ayuda para REDACTAR correos o ORDENAR información, nunca para dar asesoría legal o contable. Recomienda confirmar con un profesional.
- Recuerda siempre que la IA puede equivocarse: el tip debe incluir como verificar el resultado ("como_verificar").
- Un tip debe poder hacerse en 3 a 5 pasos, por alguien que hoy solo usa la IA como si fuera Google.
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
- "pilar": uno de los 3 pilares de Praktix ("1. Cotizaciones y Respuestas", "2. Seguimiento y Control", "3. Resúmenes de Operación")
- "cta_palabra": una sola palabra clave de estas 4: "COTIZAR", "COBRO", "INFORME" o "PRAKTIX"
- "formato": "carrusel" o "reel"
- "gancho": la primera linea que detiene el scroll (maximo 12 palabras)
- "pantallas": lista de 5 a 7 textos cortos, uno por pantalla del carrusel (o por escena del reel)
- "pie": texto de la publicacion (maximo 600 caracteres), terminando con un llamado a comentar la palabra clave elegida
- "hashtags": lista de 5 hashtags en espanol
- "que_mostrar": que imagen o captura usar, recordando incluir el rotulo 'Demo con datos ficticios' si es una simulacion
"""


def escribir(tipo: str, caso: dict | None, tema: str | None, previos: list[str], angulo: str | None = None) -> dict:
    pilares_txt = "
".join(f"- {p}" for p in PILARES_PRAKTIX)
    if tipo == "caso":
        base = f"""Escribe el borrador de una publicacion de Instagram que cuenta este caso real o demostracion operativa:
{json.dumps(caso, ensure_ascii=False, indent=2)}

ANGULO DE ESTA PUBLICACION (el caso ya se ha contado antes desde otros angulos; usa solo este): {angulo}"""
    else:
        base = f"""Escribe el borrador de una publicacion EDUCATIVA de Instagram sobre este tema operativo: "{tema}".

COMO ENSEÑAR ESTE TEMA:
- Pantalla 1: un dolor cotidiano en una Mipyme, oficina o proyecto (sin mencionar tecnologia todavia).
- Pantallas siguientes: cómo se resuelve usando las herramientas que ya tienen (Excel, correo, PDF) sin cambiar de software ni llenar tableros manuales.
- Pantalla final: una acción concreta hoy e invitación a comentar la palabra clave correspondiente ({', '.join(PALABRAS_CLAVE_CTA)}).

Conecta la idea con alguno de estos casos reales solo como ejemplo breve, sin inventar datos:
{json.dumps([{k: c[k] for k in ("titulo", "solucion", "herramientas")} for c in cargar_casos()], ensure_ascii=False)}"""
    return llamar_gemini(f"""Eres redactora de la cuenta de Instagram Praktix ("Inteligencia aplicada"), de una
profesional que automatiza procesos operativos diarios en Mipymes y proyectos (cotizaciones, seguimiento/cobranza e informes).
Enfócate estrictamente en estos 3 pilares:
{pilares_txt}

{base}

Evita repetir estos ganchos ya usados: {previos}

{REGLAS}
{REGLAS_LENGUAJE}
{FORMATO_BORRADOR}""")


def revisar(borrador: dict, tipo: str, caso: dict | None) -> dict:
    hechos = json.dumps(caso, ensure_ascii=False, indent=2) if caso else "(publicacion educativa: no debe afirmar cifras ni resultados propios)"
    return llamar_gemini(f"""Eres revisora de contenido. Revisa el borrador contra las reglas y los hechos.
Busca: cifras no confirmadas, datos inventados, nombres reales, promesas de WhatsApp no respaldadas, temas dispersos de marketing
o redes sociales, y palabras clave fuera de {PALABRAS_CLAVE_CTA}.
Busca TAMBIEN lenguaje tecnico: palabras de la lista prohibida sin explicar, frases largas, pantallas que no se
entienden solas, explicaciones que empiezan por la tecnologia en vez de por el dolor operativo diario. Reescribelas en palabras sencillas.

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
    pantallas = "
".join(f"  {i}. {t}" for i, t in enumerate(b.get("pantallas", []), 1))
    texto = (
        f"{titulo}
"
        f"Pilar: {b.get('pilar', '')} · CTA: {b.get('cta_palabra', '')}
"
        f"Formato: {b.get('formato', '')}

"
        f"Gancho: {b.get('gancho', '')}

"
        f"Pantallas:
{pantallas}

"
        f"Texto de la publicacion:
{b.get('pie', '')}

"
        f"Hashtags: {' '.join(b.get('hashtags', []))}

"
        f"Que mostrar: {b.get('que_mostrar', '')}"
    )
    if problemas:
        texto += "

La revisora corrigio: " + "; ".join(problemas)
    if "[CONFIRMAR" in texto:
        texto += "

OJO: hay datos marcados [CONFIRMAR]. Completalos o quitalos antes de publicar."
    texto += "

Revisa que no se cuele ningun dato real antes de publicar."
    return texto


# ---------------------------------------------------------------------------
# Tips de IA para trabajo operativo (Mipymes, oficinas y Project Managers)
# ---------------------------------------------------------------------------

FORMATO_TIP = """Devuelve SOLO un objeto JSON con estas claves:
- "cta_palabra": una sola palabra clave de estas 4: "COTIZAR", "COBRO", "INFORME" o "PRAKTIX"
- "tip": un objeto con:
    - "titulo": nombre corto y claro del tip (maximo 10 palabras, sin tecnicismos)
    - "para_quien": a quien le sirve en el trabajo (ej. dueños de Mipyme, equipos comerciales, Project Managers, administrativos)
    - "problema": la situacion cotidiana de oficina que resuelve, contada en 1-2 frases
    - "pasos": lista de 3 a 5 pasos muy concretos, en lenguaje sencillo
    - "instruccion_ejemplo": el texto exacto que la persona puede copiar y pegar en cualquier asistente de IA, con [huecos] para completar
    - "como_verificar": como comprobar que lo que respondio la IA esta bien (1-2 frases)
    - "cuidado": que NO hacer o que cuidar (privacidad de clientes/facturas, errores de la IA, limites)
- "para_probar": lista de 3 a 5 cosas concretas que la duena de la cuenta debe probar ella misma antes de publicar
- "datos_a_verificar": lista de afirmaciones sobre herramientas, funciones, precios o limites que podrian haber cambiado (vacia si no hay)
- "dificultad": "facil" o "medio"
- "formato": "carrusel" o "reel"
- "gancho": primera linea que detiene el scroll (maximo 12 palabras, empieza por el problema operativo, no por la tecnologia)
- "pantallas": lista de 5 a 7 textos cortos: 1 problema de oficina, 3 a 4 pasos, 1 con la instruccion lista para copiar, 1 de cuidado/cierre con CTA
- "pie": texto de la publicacion (maximo 600 caracteres), termina invitando a guardar o comentar la palabra clave
- "hashtags": lista de 5 hashtags en espanol
- "que_mostrar": que captura o imagen usar, sin datos reales de nadie
"""


def escribir_tip(categoria: str, previos: list[str], titulos_previos: list[str]) -> dict:
    return llamar_gemini(f"""Eres redactora de la cuenta de Instagram Praktix ("Inteligencia aplicada"). La cuenta enseña a dueños de Mipyme,
equipos comerciales, administrativos y Project Managers a usar la IA en su trabajo diario (más allá de usarla como un buscador).
Tu trabajo es proponer UN tip práctico de oficina que alivie una tarea repetitiva real.

CATEGORIA / PUBLICO DE ESTE TIP: {categoria}

Debe ser algo que la dueña de la cuenta pueda probar ella misma en pocos minutos, antes de publicarlo.
No repitas estos tips ya propuestos: {titulos_previos}
Evita repetir estos ganchos: {previos}

{REGLAS_TIPS}
{REGLAS_LENGUAJE}
{FORMATO_TIP}""", temperatura=0.7)


def revisar_tip(borrador: dict) -> dict:
    return llamar_gemini(f"""Eres revisora de contenido. Revisa este tip de IA para Instagram contra las reglas.
Busca: tecnicismos sin explicar, frases largas, promesas de tiempo o resultados, cifras o estudios inventados,
afirmaciones de que la cuenta ya lo uso o le funciono, consejos contables/legales/financieros directos, ejemplos con datos
confidenciales reales, pasos que dependan de funciones de pago sin avisar, temas fuera del ámbito laboral/operativo,
y palabras clave fuera de {PALABRAS_CLAVE_CTA}.
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
    pasos = "
".join(f"  {i}. {p}" for i, p in enumerate(tip.get("pasos", []), 1))
    pantallas = "
".join(f"  {i}. {t}" for i, t in enumerate(b.get("pantallas", []), 1))
    para_probar = "
".join(f"  [ ] {x}" for x in b.get("para_probar", []))
    por_verificar = "
".join(f"  - {x}" for x in b.get("datos_a_verificar", []))

    texto = (
        f"PRAKTIX · TIP {numero} de {total}: {tip.get('titulo', '')}
"
        f"Publico: {categoria}
"
        f"CTA: {b.get('cta_palabra', '')} · Dificultad: {b.get('dificultad', '')} · Formato: {b.get('formato', '')}

"
        f"PARA QUIEN: {tip.get('para_quien', '')}
"
        f"EL PROBLEMA: {tip.get('problema', '')}

"
        f"PASOS:
{pasos}

"
        f"INSTRUCCION PARA COPIAR Y PEGAR:
{tip.get('instruccion_ejemplo', '')}

"
        f"COMO REVISAR LO QUE RESPONDA: {tip.get('como_verificar', '')}
"
        f"CUIDADO: {tip.get('cuidado', '')}
"
        f"
--- BORRADOR DE LA PUBLICACION ---
"
        f"Gancho: {b.get('gancho', '')}

"
        f"Pantallas:
{pantallas}

"
        f"Texto de la publicacion:
{b.get('pie', '')}

"
        f"Hashtags: {' '.join(b.get('hashtags', []))}

"
        f"Que mostrar: {b.get('que_mostrar', '')}
"
        f"
--- ANTES DE PUBLICAR, PRUEBALO TU ---
{para_probar}"
    )
    if por_verificar:
        texto += f"

DATOS POR VERIFICAR (pueden haber cambiado):
{por_verificar}"
    if problemas:
        texto += "

La revisora corrigio: " + "; ".join(problemas)
    texto += (
        "

ESTADO: sin probar. Este tip lo propuso la IA; no lo publiques hasta que lo hayas practicado "
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
    entregar(formatear(f"PRAKTIX · Borrador 1 (caso): {caso['titulo']}
Angulo: {angulo.split(':')[0]}", b1, p1), seco)
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
        f"PRAKTIX · Tips de IA operativos de la semana ({hoy})
"
        f"Te llegan {total} tips para oficina, Mipymes y Project Managers. Pruebalos tu antes de publicar.",
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
            guardar_historial(hist)


def modo_kit(seco: bool) -> None:
    casos = cargar_casos()
    pilares_txt = "
".join(f"- {p}" for p in PILARES_PRAKTIX)
    plan = llamar_gemini(f"""Eres estratega de contenido. Prepara el plan del Mes 1 de Instagram de Praktix (12 publicaciones: 3 por semana durante 4 semanas, lunes/miércoles/viernes).
Praktix se enfoca exclusivamente en aliviar el trabajo operativo diario de Mipymes y Project Managers alrededor de estos 3 pilares:
{pilares_txt}

Distribución semanal recomendada:
- Lunes: Atracción / Tip práctico de IA en oficina (correos, actas de reunión, tablas Excel).
- Miércoles: Demostración de solución o caso real (respuestas en borradores, informe semanal HTML, cotizador PDF, caso 500 informes, seguimiento automático por correo).
- Viernes: Diagnóstico de dolor operativo y conversión (4 señales de trabajo de robot, prompts comerciales, costo oculto de perseguir pendientes, filtro de 3 preguntas).

Cada publicación debe usar UNA palabra clave CTA de estas 4: {', '.join(PALABRAS_CLAVE_CTA)}.

CASOS (unica fuente de hechos):
{json.dumps(casos, ensure_ascii=False, indent=2)}

{REGLAS}
{REGLAS_LENGUAJE}

Devuelve SOLO un objeto JSON con:
- "publicaciones": lista de 12 objetos con "numero", "semana", "dia", "pilar", "cta_palabra", "tipo", "titulo", "formato", "gancho", "idea" (2 lineas), "que_mostrar"
- "historias": lista de 4 textos cortos de historias para la primera semana
""")
    lineas = ["PRAKTIX · Kit de lanzamiento (Mes 1 · 12 Publicaciones)", "", "Bio elegida:", BIO, "",
              "Nombre del perfil: Praktix | Automatización e IA Operativa",
              "Destacadas: Cotizaciones · Seguimiento · Informes · Casos · Contacto", "", "Plan de 4 semanas (3 publicaciones/semana):"]
    for p in plan.get("publicaciones", []):
        lineas.append(
            f"
{p.get('numero')}. (Sem. {p.get('semana')} - {p.get('dia')} | {p.get('pilar')} | CTA: {p.get('cta_palabra')} | {p.get('formato')}) {p.get('titulo')}
"
            f"   Gancho: {p.get('gancho')}
   Idea: {p.get('idea')}
   Mostrar: {p.get('que_mostrar')}"
        )
    lineas.append("
Historias de la primera semana:")
    lineas += [f"  - {h}" for h in plan.get("historias", [])]
    lineas.append("
Antes de publicar: revisa que ninguna imagen o texto tenga datos reales, y completa lo marcado [CONFIRMAR].")
    entregar("
".join(lineas), seco)


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
