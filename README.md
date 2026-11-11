# Degiro Renta

CLI que calcula la fiscalidad IRPF a partir del extracto de cuenta de Degiro: parsea el
fichero, casa las ventas por FIFO y muestra las tablas por terminal.

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
