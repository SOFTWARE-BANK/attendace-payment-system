# Instrucciones de uso de la plantilla Shadcn-UI

## Tecnologias

Este proyecto utiliza:

- Vite
- TypeScript
- React
- shadcn-ui
- Tailwind CSS

Todos los componentes de shadcn/ui se encuentran en `@/components/ui`.

## Estructura de archivos

- `index.html` - punto de entrada HTML
- `vite.config.ts` - archivo de configuracion de Vite
- `tailwind.config.ts` - Tailwind CSS configuration file
- `package.json` - NPM dependencies and scripts
- `src/main.tsx` - punto de entrada del proyecto
- `src/App.tsx` - shell del router (importa paginas y configura rutas)
- `src/pages/Index.tsx` - punto de entrada principal para `/`; reemplaza aqui el marcador de posicion salvo que redirijas la ruta de forma explicita
- `src/index.css` - configuracion CSS existente

## Componentes

- Todos los componentes de shadcn/ui estan descargados y disponibles en `@/components/ui`.

## Estilos

- Agrega estilos globales en `src/index.css` o crea archivos CSS nuevos cuando sea necesario.
- Usa clases de Tailwind para aplicar estilos a los componentes.

## Desarrollo

- Importa los componentes desde `@/components/ui` en tus componentes React.
- Personaliza la interfaz modificando la configuracion de Tailwind.
- No termines despues de editar componentes aislados o solo `src/App.tsx`. La pagina inicial de la plantilla esta en `src/pages/Index.tsx`; si conserva `Welcome to Atoms`, la aplicacion sigue incompleta.
- Comprobacion final: reemplaza `src/pages/Index.tsx` con la pagina inicial real o actualiza la ruta `/` en `src/App.tsx` para que la pagina activa ya no muestre el marcador de posicion.

## Nota

- El alias de ruta `@/` apunta al directorio `src/`.
- No modifiques el titulo, la descripcion ni el logo de `index.html`: el sistema de resumen los administra mediante marcadores `data-mgx-overview`.

# Comandos

**Instalar dependencias**

```shell
pnpm i
```

**Iniciar vista previa**

```shell
pnpm run dev
```

**Construir**

```shell
pnpm run build
```
