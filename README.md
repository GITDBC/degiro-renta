<p align="center">
  <a href="https://github.com/GITDBC/degiro-renta/actions/workflows/workflow.yml">
    <img src="https://github.com/GITDBC/degiro-renta/actions/workflows/workflow.yml/badge.svg">
  </a>
  <a href="https://github.com/GITDBC/degiro-renta/blob/main/LICENSE" target="_blank">
    <img src="https://img.shields.io/github/license/GITDBC/degiro-renta" alt="License">
  </a>
</p>

# Degiro Renta

CLI que calcula la fiscalidad IRPF a partir del extracto de cuenta de Degiro: parsea el
fichero, casa las ventas por FIFO y muestra las tablas por terminal.

> **Aviso.** Este proyecto no tiene ninguna relación, afiliación ni vínculo con Degiro.
> Es una herramienta independiente. No me hago responsable de los fallos, errores o
> cálculos incorrectos que pueda producir, ni de las decisiones que tomes a partir de
> sus resultados. No es asesoramiento fiscal ni sustituye a un profesional. Revisa
> siempre las cifras antes de presentar tu declaración.

## Uso

```bash
uv run degiro-renta tax holdings/Account.xlsx
```

El fichero es el XLSX de _Estado de cuenta_ exportado de Degiro. No hace ninguna llamada
de red.

## Informe fiscal

Integra en una sola base del ahorro todo lo que tributa por la escala del art. 66 LIRPF:
las **ganancias patrimoniales** de las ventas, casadas por FIFO por ISIN, y los
**rendimientos del capital mobiliario** (dividendos brutos e intereses). Después resta
las retenciones españolas, que son pago a cuenta y no impuesto definitivo.

Bloques que conviene conocer:

- **Resultado realizado por año**: solo aparece si el extracto abarca varios ejercicios.
- **Detalle para la declaración**: una línea por fecha de adquisición, lista para
  teclear en Renta Web.
- **Posibles pérdidas no imputables**: candidatas a la regla de los dos meses (art.
  33.5.f LIRPF); el importe sigue dentro de la base porque decidir si se difiere exige
  valorar la homogeneidad en todos tus brokers, algo que un extracto no resuelve.
- **Operaciones excluidas**: órdenes en divisa sin cambio asociado (cuenta Manual FX);
  se excluye todo el historial de ese ISIN porque no se puede expresar en euros.

Ninguna fila del extracto se descarta en silencio: lo que no encaja en ningún concepto se
avisa por log con su descripción.
