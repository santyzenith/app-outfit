# Proyecto: App de armario virtual

## Qué es
App móvil que responde "¿qué me pongo hoy?". El usuario fotografía su ropa,
la IA la cataloga automáticamente, y la app propone un outfit diario armado
únicamente con prendas que ya posee. Sin compras ni e-commerce.

Momento de uso principal: 7am, medio dormido, con una mano, 30 segundos.
Público unisex, hispanohablante.

## Estado del proyecto
Reconstruido desde cero en octubre de 2026; el intento anterior se eliminó.
Monorepo en `github.com/santyzenith/app-outfit`: `backend/` (API y worker),
`mobile/` (app), `docker-compose.yml` (entorno local) e `image_spike/`
(pruebas de modelos de imagen).

## Stack

**App móvil**
- React Native + Expo (SDK actual) con TypeScript
- Expo Router (navegación basada en archivos)
- NativeWind (Tailwind)
- React Native Reusables — componentes en `components/ui/`
- TanStack Query (estado de servidor) + Zustand (estado local)
- EAS Build para builds y distribución. Se desarrolla en Windows y se
  prueba en Android; iOS se compila en la nube al final.

**Backend**
- Python + FastAPI, API REST
- PostgreSQL propio como servicio de Docker Compose (sin Supabase).
  SQLAlchemy + Alembic.
- Auth propia: el móvil obtiene el ID token de Google/Apple con el SDK
  nativo, FastAPI lo verifica y emite su sesión (access JWT de corta
  duración + refresh token rotativo guardado en la base). El móvil guarda
  los tokens en almacenamiento seguro y los envía en el header
  `Authorization`. Sin cookies.
- Storage: disco local, una carpeta por usuario; la base guarda solo la
  ruta relativa. Siempre detrás de una capa de abstracción propia para
  poder migrar a un almacenamiento externo. Las fotos se comprimen en el
  teléfono y se suben a través de FastAPI.
- Procesamiento de fotos en segundo plano con una cola de trabajos durable
  en Postgres y un proceso worker aparte. Nunca `BackgroundTasks` de
  FastAPI, nunca bloqueante.
- IA por API vía OpenRouter (sin modelos locales en el servidor), detrás de
  una capa de abstracción propia (`sugerir_outfit`, `analizar_prenda`,
  `extraer_estilo`). NUNCA llamar a OpenRouter directamente desde los
  endpoints.
- Imagen de la prenda: un modelo generativo recrea la prenda de la foto del
  usuario como imagen limpia de catálogo. Modelo elegido tras la prueba de
  `image_spike/`: `bytedance-seed/seedream-5-0-flash` (unos $0.018 por
  imagen). El nombre del modelo es configuración, no código. Siempre se
  guarda la foto original. Los prompts a modelos van en inglés.
- Sacar varias prendas de una misma foto solo funciona si cada prenda está
  extendida y visible; con prendas dobladas o tapadas el modelo inventa.

**Despliegue**
- Docker Compose en un VPS propio: API, worker, Postgres y proxy HTTPS.
  Dominio en Cloudflare, API en un subdominio. Se configura al final; por
  ahora todo corre en local.
- Backups automáticos de la base y de las fotos fuera del VPS.

## Reglas de código

- Español para textos de UI (neutro latinoamericano, tuteo); inglés para
  código, nombres de variables y comentarios.
- APIs modernas de Expo Router y NativeWind. PROHIBIDO: `StyleSheet.create`,
  class components, configuración manual de React Navigation.
- Nada de patrones web: no hover, no CSS grid, no cascada de estilos.
- Todo texto dentro de `<Text>`.
- Los componentes de `components/ui/` se dejan como vienen de React Native
  Reusables. Para ajustarlos se pasan clases Tailwind por `className` donde
  se usan; no se edita el archivo del componente. Única excepción: la
  clase `font-sans` en `components/ui/text.tsx`, porque en móvil la fuente
  por defecto no se hereda y solo se puede fijar ahí.
- Tipografía: Hanken Grotesk para la interfaz y Newsreader para títulos y
  la frase del outfit. Cada peso es una familia aparte (`font-sans-medium`,
  `font-sans-semibold`, `font-sans-bold`, `font-serif-medium`,
  `font-serif-italic`); no usar `font-medium`/`font-bold` sueltos, en
  Android no cambian el peso de una fuente propia.
- Un solo repositorio para backend y app (monorepo).
- Colores siempre desde los tokens del tema, nunca hex fijos en pantallas.
- El móvil solo habla con FastAPI vía HTTP/JSON. Nunca con proveedores de IA
  directamente.
- Tests y git desde el primer commit.

## Decisiones de producto ya tomadas (no proponer alternativas)

- Home abre con el outfit YA generado y guardado (el del día y sus
  alternativas se pregeneran). Sin formularios ni configuración.
- UN outfit a la vez, grande, con botón discreto de "otra".
- Composición de un outfit:
  - Base (obligatoria): parte de arriba + parte de abajo, o una pieza
    entera (vestido, enterizo).
  - Capa (opcional): chaqueta, suéter o abrigo, según el clima.
  - Zapatos (obligatorios).
  - Accesorio (opcional, uno): bolso, gorra, bufanda.
  - Fuera de la primera versión: joyería, cinturones, medias, ropa interior.
- Los outfits se renderizan como collage de imágenes de prendas, con zonas
  fijas según esa composición.
- El outfit se arma en dos pasos: el código filtra candidatos (clima,
  ocasión, usado hace poco) y el LLM elige entre esa lista corta y escribe
  la explicación.
- Ocasión mediante chips, uno preseleccionado según día y hora.
- Cada outfit incluye una explicación breve en lenguaje natural.
- El usuario registra lo que se puso ("Me lo pongo"). Eso evita repetir
  prendas recién usadas, con un descanso distinto según el tipo de prenda.
  NO hay función de lavandería.
- Login solo con Google y Apple.
- Modo claro y oscuro siguiendo el sistema. En modo oscuro, el lienzo del
  collage se mantiene claro (los recortes se ven mal sobre fondo oscuro).

## Posicionamiento
- Una sola cosa bien hecha: abrir la app y tener el outfit de hoy decidido.
  No es un menú de herramientas.
- Un estilista confiable: nunca sugiere algo que no va con el clima ni
  repite lo recién usado, y rota todo el armario.
- Hecha para Latinoamérica: español real, y las prendas se catalogan por
  nivel de abrigo (ligero, medio, abrigado), no por temporada.
- Se puede usar sin registrarse: la app crea una cuenta de invitado y el
  login con Google/Apple se pide después y se vincula a esa cuenta.
- Sin comunidad, anuncios ni estadísticas.

## A futuro (no construir todavía)
- El diferenciador a largo plazo: partir de un look de referencia (una
  foto, o una publicación de un influencer que el usuario comparte a la
  app) y armarlo con lo que el usuario ya tiene. Es la evolución de
  "Inspira".
- Búsqueda por similitud con embeddings de las prendas (la base usa una
  imagen de Postgres con pgvector para no migrar después).
- Probador virtual y análisis de color.
- Descartado: importar de tiendas y extensión de navegador.

## Competidor de referencia
Acloset (acloset.app): 8M+ usuarios, gratis hasta 100 prendas y luego
suscripción. Hace mucho más que nosotros (probador virtual, estadísticas,
importar de tiendas, comunidad, viajes). Su Home es un menú de
herramientas; el outfit del día es una función entre muchas. Las quejas de
sus usuarios se concentran en la calidad del estilista (ignora clima y
temporada, repite prendas), el muro de pago a las 100 prendas y los fallos.

## Orden de construcción

1. Prueba de imágenes (`image_spike/`).
2. Base del backend y login.
3. Subir y catalogar prendas.
4. Pantalla Hoy.
5. Armario.
6. Historial.
7. Inspira (look de referencia → estilo).

## El problema más difícil
El onboarding. La gente tiene 100+ prendas. Si subir ropa se siente como
llenar formularios, abandonan antes de recibir valor. Optimizar ese flujo
por encima de todo lo demás.
