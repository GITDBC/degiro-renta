<p align="center">
  <a href="https://github.com/GITDBC/degiro-renta/actions/workflows/workflow.yml">
    <img src="https://github.com/GITDBC/degiro-renta/actions/workflows/workflow.yml/badge.svg">
  </a>
  <a href="https://github.com/GITDBC/degiro-renta/blob/main/LICENSE" target="_blank">
    <img src="https://img.shields.io/github/license/GITDBC/degiro-renta" alt="License">
  </a>
</p>

# Degiro Renta

CLI que calcula la base del ahorro del IRPF a partir del extracto de Degiro: lee el
archivo, casa las ventas por FIFO y muestra las tablas por terminal.

> **Aviso.** Este proyecto no tiene ninguna relación, afiliación ni vínculo con Degiro.
> Es una herramienta independiente y no es asesoramiento fiscal. No se responde de los
> errores de cálculo ni de las decisiones que se tomen a partir de sus resultados.
> Conviene revisar siempre las cifras antes de presentar la declaración.

## Uso

```bash
uv run degiro-renta tax holdings/Account.xlsx
```

Para ver los ejercicios con actividad y calcular uno concreto:

```bash
uv run degiro-renta years holdings/Account.xlsx
uv run degiro-renta tax holdings/Account.xlsx --year 2026
```

Sin `--year` se calcula el último ejercicio con actividad. El extracto se procesa
entero, porque el FIFO y la regla de los dos meses usan todo el historial, aunque el
informe sea de un solo ejercicio. El archivo es el XLSX de _Estado de cuenta_ exportado
de Degiro. La herramienta no hace ninguna llamada de red.

## Documentación

La normativa que aplica el cálculo, con sus referencias a la ley, a las consultas de la
DGT y a los enlaces oficiales, está en [`docs/`](docs/index.md). Cada sección del
informe tiene su página, y el mapa está en la portada. Los supuestos sin respuesta
normativa se recogen en
[cuestiones abiertas](docs/03_cuestiones_abiertas/section_1_fundamentals.md).
