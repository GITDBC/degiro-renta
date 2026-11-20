---
icon: lucide/landmark
title: Modelo 720
description:
    Obligación informativa de los bienes y derechos situados en el extranjero, con sus
    umbrales, plazos, valoración y régimen sancionador.
---

El modelo 720 es una declaración informativa de los bienes y derechos que un residente
en España posee en el extranjero. No liquida impuesto, pero su falta de presentación se
sanciona. Esta página resume cuándo es obligatorio, qué se valora y cuándo debe
repetirse.

## Bibliografía

- Real Decreto 1065/2007, de 27 de julio, Reglamento General de las actuaciones y los
  procedimientos de gestión e inspección tributaria, arts. 42 bis y 42 ter.
  [BOE](https://www.boe.es/buscar/act.php?id=BOE-A-2007-15984).
- Orden HAP/72/2013, de 30 de enero, por la que se aprueba el modelo 720, arts. 2 y 7.
  [BOE](https://www.boe.es/buscar/act.php?id=BOE-A-2013-954).
- Orden HFP/1180/2023, de 26 de octubre, que modifica la Orden HAP/72/2013 y la Orden
  EHA/3481/2008. [BOE](https://www.boe.es/buscar/act.php?id=BOE-A-2023-22221).
- AEAT,
  [preguntas frecuentes sobre el modelo 720](https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/impuestos-tasas/declaraciones-informativas/modelo-720-decla_____sobre-bienes-derechos-extranjero_/preguntas-frecuentes/valoracion.html).
- Ley 19/1991, de 6 de junio, del Impuesto sobre el Patrimonio, art. 15.

## Obligados y bienes

Están obligados los residentes en territorio español que sean titulares, autorizados o
beneficiarios de bienes situados en el extranjero (art. 2 de la Orden HAP/72/2013, en la
redacción de la Orden HFP/1180/2023). La declaración tiene tres bloques: las cuentas en
entidades financieras (art. 42 bis RGGI), los valores, derechos, seguros y rentas (art.
42 ter RGGI) y los inmuebles (art. 54 bis RGGI).

## Umbrales

Cada bloque tiene su propio límite de 50.000 euros.

- **Cuentas**: no hay obligación si los saldos a 31 de diciembre no superan, en
  conjunto, esa cifra, ni tampoco los saldos medios del último trimestre (art. 42
  bis.4.e RGGI). Si se supera cualquiera de los dos límites, se informa de todas las
  cuentas.
- **Valores, IIC y seguros**: el límite es conjunto para el saldo de los valores, el
  valor liquidativo de las instituciones de inversión colectiva y el valor de rescate de
  los seguros (art. 42 ter.4.c RGGI). Si se supera, se informa de todos.

Según la AEAT, los saldos negativos se netean con los positivos al calcular el límite.

## Plazo y repetición

La declaración se presenta del 1 de enero al 31 de marzo del año siguiente (art. 42
bis.5 y 42 ter.5 RGGI, y art. 7 de la Orden HAP/72/2013). En los años siguientes solo es
obligatoria si el valor conjunto aumenta más de 20.000 euros respecto del que motivó la
última declaración, o si se extingue la titularidad de un bien ya declarado.

Según la AEAT, la venta de valores ya declarados obliga a informar de su cancelación. Si
lo obtenido se reinvierte íntegramente, menos gastos y comisiones, basta declarar los
saldos a 31 de diciembre. La compra y venta dentro del mismo año, sin declaración
previa, no genera obligación.

## Valoración

Los valores se valoran según las reglas del Impuesto sobre el Patrimonio (art. 42 ter.6
RGGI). Las acciones negociadas en un mercado organizado se valoran por su cotización
media del cuarto trimestre (art. 15 de la Ley 19/1991), o por su cotización a 31 de
diciembre si se negocian en un mercado extranjero de características análogas a las
españolas (AEAT). Las instituciones de inversión colectiva, incluidos los ETF, se
declaran por su valor liquidativo a 31 de diciembre. Los saldos en divisa se convierten
al tipo de cambio de esa fecha.

## Entidades españolas

Los valores depositados en entidades establecidas en España que informan de ellos a la
Administración quedan fuera de la obligación (AEAT, en relación con el art. 42 ter.1
RGGI).

## Sanciones

La falta de presentación se sanciona con el régimen general de los artículos 198 y 199
de la Ley 58/2003, General Tributaria, desarrollado en los artículos 14 y 15 del Real
Decreto 2063/2004. Las sanciones se aplican de forma independiente a cada uno de los
tres bloques. La Ley 5/2022 adaptó este régimen a la sentencia del Tribunal de Justicia
de la Unión Europea de 27 de enero de 2022, en el asunto C-788/19.

!!! note

    La normativa no define expresamente si los valores custodiados por un bróker no
    español están situados en el extranjero. Véase [cuestiones
    abiertas](../03_cuestiones_abiertas/section_1_fundamentals.md).

## Qué hace la herramienta

La herramienta no calcula el modelo, porque el extracto no trae el valor de mercado a 31
de diciembre. Avisa por bloque cuando la cifra que sí conoce alcanza la mitad del
umbral, y en rojo cuando lo supera:

- **Valores e IIC**: el coste de adquisición de las posiciones abiertas, por FIFO, a 31
  de diciembre o a la última fecha del extracto si es anterior.
- **Cuentas**: el mayor entre el saldo en euros a esa fecha y la media de los saldos en
  euros desde el 1 de octubre. No suma los saldos en otras divisas. Excluye las
  transferencias entre la cuenta de valores y la cuenta de efectivo (_Cash Sweep_),
  porque dejan saldos transitorios que no reflejan el efectivo del titular.

Ese aviso no sustituye el cálculo de la obligación a 31 de diciembre con los valores de
mercado, ni sabe si el modelo se presentó en un año anterior, que cambia cuándo hay que
repetirlo.
