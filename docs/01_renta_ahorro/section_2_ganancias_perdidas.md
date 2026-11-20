---
icon: lucide/trending-up
title: Ganancias y pérdidas patrimoniales
description:
    Cálculo de las ganancias y pérdidas patrimoniales por la transmisión de valores, con
    los valores de adquisición y transmisión y el orden de identificación de los
    títulos.
---

Las ganancias y pérdidas patrimoniales recogen las variaciones del patrimonio que se
producen al transmitir un elemento, como la venta de valores. Esta página fija cómo se
calculan y qué valores se toman como base.

## Bibliografía

- Ley 35/2006, de 28 de noviembre, del Impuesto sobre la Renta de las Personas Físicas,
  arts. 14, 33, 34, 35, 37 y 49.
  [BOE](https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764).
- Real Decreto 439/2007, de 30 de marzo, Reglamento del Impuesto sobre la Renta de las
  Personas Físicas, art. 8. [BOE](https://www.boe.es/buscar/act.php?id=BOE-A-2007-6820).
- Agencia Tributaria, _Manual práctico de Renta 2025_, capítulo 11.
  [Pérdidas patrimoniales que no se computan](https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/irpf-2025/c11-ganancias-perdidas-patrimoniales/ganancias-perdidas-patrimoniales-que-no-bi/perdidas-patrimoniales-que-no-se-tales.html).
- DGT, consulta vinculante
  [V0152-26](https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V0152-26),
  sobre comisiones y divisas.

## Introducción

Según el artículo 33.1 LIRPF, son ganancias y pérdidas patrimoniales las variaciones en
el valor del patrimonio que se ponen de manifiesto con una alteración en su composición.
La **ganancia o pérdida** es la diferencia entre el valor de transmisión y el valor de
adquisición (art. 34.1.a LIRPF). Se imputa al período impositivo en que tiene lugar la
alteración patrimonial (art. 14.1.c LIRPF).

## Valores de adquisición y de transmisión

El valor de adquisición suma el importe real pagado y los gastos y tributos inherentes a
la compra, excluidos los intereses (art. 35.1 LIRPF). El valor de transmisión es el
importe real de la venta, del que se restan los gastos y tributos de la venta que el
transmitente ha satisfecho (art. 35.2 LIRPF). Las comisiones de compra y de venta de
valores forman parte, así, de cada valor (V0152-26).

El valor de transmisión no puede ser inferior al valor normal de mercado (art. 35.2
LIRPF). Para los valores admitidos a negociación en mercados regulados, la transmisión
se valora por la cotización en la fecha de la operación, o por el precio pactado si este
es superior (art. 37.1.a LIRPF).

## Valores homogéneos y orden de transmisión

Son homogéneos los valores de un mismo emisor que forman parte de una misma operación
financiera, tienen la misma naturaleza y régimen de transmisión y atribuyen derechos
sustancialmente iguales (art. 8 RIRPF). Cuando existen valores homogéneos, se considera
que se transmiten los adquiridos en primer lugar (art. 37.2 LIRPF). Es la regla FIFO,
que la herramienta aplica por ISIN.

## Otros supuestos

- **Acciones liberadas**: el coste total se reparte entre todos los títulos, antiguos y
  nuevos, y las acciones heredan la antigüedad de las que proceden (art. 37.1.a LIRPF).
- **Derechos de suscripción**: su transmisión genera una ganancia en el período en que
  se produce (art. 37.1.a LIRPF).
- **Reducción de capital**: no genera ganancia. Se consideran amortizadas las acciones
  adquiridas en primer lugar (art. 33.3.a LIRPF).
- **Incorporaciones sin transmisión**: se computa como ganancia el valor de mercado de
  los bienes incorporados (art. 37.1.l LIRPF).

!!! note

    La distribución de prima de emisión no es una ganancia patrimonial. Minora el valor
    de adquisición y su exceso es rendimiento del capital mobiliario (art. 25.1.e
    LIRPF). Se trata en la [página de rendimientos](section_5_rendimientos.md).

Las ganancias y pérdidas se integran y compensan entre sí dentro de su bloque. Si el
resultado es negativo, la pérdida neta se compensa con el saldo positivo del bloque de
rendimientos del capital mobiliario, con el límite del 25 por ciento de ese saldo (art.
49.1.b LIRPF). Las pérdidas que la regla de los dos meses difiere se tratan en la
[página siguiente](section_3_regla_dos_meses.md).
