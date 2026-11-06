# Agente Praktix

Genera borradores de publicaciones de Instagram y los envía a tu Telegram.

- `python praktix_agente.py --kit`: una sola vez. Bio, destacadas y plan de 8 publicaciones.
- `python praktix_agente.py --semana`: 2 borradores (1 caso + 1 educativa). En GitHub corre lunes y jueves a las 8:00 a. m.
- Agrega `--seco` para ver el resultado en pantalla sin enviar.

## Archivos
- `casos.json`: tus casos. Es la única fuente de hechos del agente. Si confirmas una cifra, muévela de `cifras_por_confirmar` a `cifras_confirmadas`.
- `historial.json`: lo ya propuesto, para no repetir casos, temas ni ganchos.
- `.github/workflows/praktix.yml`: el despertador. Usa los mismos 3 secretos del agente de noticias.

## Cómo funciona
Una IA escribe el borrador; otra lo revisa contra tus reglas (sin cifras sin confirmar, sin nombres reales, sin afirmar revisión profesional si no consta). Lo que encuentre, lo corrige y te lo avisa. Aun así, tú revisas siempre antes de publicar.
