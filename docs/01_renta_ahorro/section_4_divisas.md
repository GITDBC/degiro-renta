---
icon: lucide/globe
title: Divisas
description:
    Tributación de las diferencias de cambio en cuentas en divisa, de los valores
    negociados en otra moneda y de las pérdidas por tipo de cambio.
---

Las operaciones en divisa afectan al IRPF de dos formas: por las diferencias de cambio
de los saldos en una cuenta en moneda extranjera y por la compra y venta de valores
cotizados en otra moneda. Esta página recoge el tratamiento legal de cada caso y las
consultas que lo desarrollan.

## Bibliografía

- Ley 35/2006, de 28 de noviembre, del Impuesto sobre la Renta de las Personas Físicas,
  arts. 14.1.a, 14.2.e, 33.1, 33.5.e y 35.
  [BOE](https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764).
- DGT, consultas vinculantes
  [V0152-26](https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V0152-26),
  [V1740-17](https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V1740-17),
  [V2422-20](https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V2422-20) y
  [V1613-25](https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V1613-25).

## Saldos en divisa

Las diferencias positivas o negativas de las cuentas en divisas, producidas por la
variación de su cotización, se imputan en el momento del cobro o del pago (art. 14.2.e
LIRPF). Hasta esa conversión no hay ganancia ni pérdida patrimonial.

Cuando el cambio de divisa se produce sin una operación de valores, la conversión genera
una ganancia o pérdida patrimonial. Su importe es la diferencia entre el valor de
transmisión de la divisa, al tipo de cambio de la conversión, y su valor de adquisición
(V1613-25, que reproduce la V0463-21). Esa ganancia o pérdida se integra en el bloque de
ganancias y pérdidas patrimoniales de la base del ahorro (art. 49.1.b LIRPF).

!!! note

    La herramienta aplica este criterio a los cambios de divisa del extracto que no van
    unidos a una compra o venta de valores. Casa las unidades vendidas con las
    compradas por orden de antigüedad (FIFO), una cola por moneda. Si vende unidades
    sin compra previa en el extracto, no calcula esa ganancia y avisa. La normativa no
    fija el orden de las unidades. Véase [cuestiones
    abiertas](../03_cuestiones_abiertas/section_1_fundamentals.md).

## Valores negociados en otra moneda

La DGT ha fijado el método para las acciones cotizadas en otra moneda (V1740-17,
V0152-26 y V2422-20):

- La ganancia o pérdida se calcula en la moneda en que están denominadas las acciones,
  con sus valores de adquisición y transmisión.
- La diferencia resultante se convierte a euros al tipo de cambio vigente en la fecha de
  la transmisión.
- Si el resultado en la moneda del valor es cero, no hay ganancia ni pérdida por la
  conversión posterior de los importes a euros (V2422-20).

!!! note

    La herramienta valora cada compra y cada venta con los euros que el bróker cargó o
    abonó en la orden, que es el importe real del artículo 35 LIRPF. Ninguna consulta
    resuelve si ese criterio es equivalente al de la DGT cuando el bróker convierte
    automáticamente cada orden. Véase [cuestiones
    abiertas](../03_cuestiones_abiertas/section_1_fundamentals.md).

## Pérdidas por tipo de cambio

Las pérdidas por variación del tipo de cambio no se rigen por la regla de los dos meses
de las letras f) y g) del artículo 33.5, sino por el plazo de un año del artículo 33.5.e
LIRPF (V1613-25). Si el contribuyente vuelve a adquirir la divisa dentro del año
siguiente, la pérdida se integra cuando se transmita la divisa de nuevo.

!!! note

    La herramienta no aplica esta regla: computa la pérdida de cada cambio de divisa en
    el ejercicio en que se produce, aunque se vuelva a comprar la divisa dentro del año.

## Dividendos en moneda extranjera

El artículo 14.1.a LIRPF fija el período en que se imputa el rendimiento, cuando es
exigible. Ninguna consulta leída fija el tipo de cambio que debe aplicarse para
convertir un dividendo cobrado en otra moneda. Véase
[cuestiones abiertas](../03_cuestiones_abiertas/section_1_fundamentals.md).
