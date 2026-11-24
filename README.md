# Agente Praktix

Genera borradores de publicaciones de Instagram y los envía a tu Telegram.

- `python praktix_agente.py --kit`: una sola vez. Bio, destacadas y plan de 8 publicaciones.
- `python praktix_agente.py --semana`: 2 borradores (1 caso + 1 educativa). En GitHub corre lunes y jueves a las 8:00 a. m.
- `python praktix_agente.py --tips`: 3 tips de IA para todo público, cada uno para un público distinto. En GitHub corre una vez por semana. Usa `--n=5` para cambiar la cantidad.
- Agrega `--seco` para ver el resultado en pantalla sin enviar.

## Archivos
- `casos.json`: tus casos. Es la única fuente de hechos del agente. Si confirmas una cifra, muévela de `cifras_por_confirmar` a `cifras_confirmadas`.
- `historial.json`: lo ya propuesto, para no repetir casos, temas, tips ni ganchos.
- `.github/workflows/praktix.yml`: el despertador. Usa los mismos 3 secretos del agente de noticias.

## Cómo funciona
Una IA escribe el borrador; otra lo revisa contra tus reglas (sin cifras sin confirmar, sin nombres reales, sin afirmar revisión profesional si no consta, sin tecnicismos sin explicar). Lo que encuentre, lo corrige y te lo avisa. Aun así, tú revisas siempre antes de publicar.

## Los tips de IA
Los tips son **propuestas de la IA, no hechos tuyos**. No usan `casos.json`: son consejos generales para que cualquier persona le saque provecho a la IA en su día a día (casa, estudio, oficina, negocio, familia, escribir, planear, idiomas, decisiones).

Cada tip llega con:
- Problema cotidiano, pasos, y una instrucción lista para copiar y pegar en cualquier asistente de IA.
- Cómo verificar lo que responda la IA, y qué cuidar (privacidad, errores, límites).
- **Antes de publicar, pruébalo tú**: lista de cosas para practicar tú misma.
- **Datos por verificar**: herramientas, funciones o límites que pueden haber cambiado.
- Un borrador de carrusel o reel.

Flujo recomendado: llega el tip a Telegram → lo practicas → si funciona, lo publicas; si no, lo descartas o lo ajustas.

Cada tip queda en `historial.json` con `"estado": "por_probar"`. Si quieres llevar el control, cámbialo a mano a `"probado"` o `"publicado"` (el agente no lo usa todavía, es solo para tu seguimiento).

## Si algo falla
El agente te avisa por Telegram. Revisa la pestaña **Actions** en GitHub. Los tips se guardan uno a uno en `historial.json`, así que si falla uno no se pierden los anteriores.
