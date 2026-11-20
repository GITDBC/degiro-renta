---
icon: lucide/circle-help
title: Cuestiones abiertas
description:
    Supuestos sin respuesta en la normativa ni en las consultas de la DGT, con el
    tratamiento que aplica la herramienta y lo necesario para cerrarlos.
---

Esta página recoge los supuestos que la normativa y las consultas leídas no resuelven.
Para cada uno se indica el tratamiento que aplica la herramienta, de forma que el
informe sea explícito sobre el criterio elegido.

## Bibliografía

- DGT, consultas vinculantes
  [V0152-26](https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V0152-26),
  [V1613-25](https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V1613-25),
  [V2117-19](https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V2117-19),
  [V1740-17](https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V1740-17),
  [V2422-20](https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V2422-20),
  [V0754-26](https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V0754-26),
  [V0571-21](https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V0571-21) y
  [V0778-25](https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V0778-25).
- Ley 35/2006, de 28 de noviembre, del Impuesto sobre la Renta de las Personas Físicas,
  arts. 14.1.a, 25.2.a.2.º, 25.2.b, 26.1.a, 33.1, 33.5.g, 35, 37.1.l, 37.2, 45 y 80.
  [BOE](https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764).

## Supuestos abiertos

- **Conversión automática de divisas**: las consultas sobre acciones en divisa suponen
  una cuenta abierta en esa moneda. La herramienta valora cada orden con los euros que
  el bróker cargó o abonó, que es el importe real del artículo 35 LIRPF. Para cerrarlo
  hace falta una consulta vinculante sobre una cuenta con conversión por orden.
- **Dividendos en moneda extranjera**: ninguna fuente fija el tipo de cambio. La
  herramienta usa el tipo implícito de la liquidación del bróker y excluye con aviso el
  dividendo si no lo hay.
- **Comisión de conectividad con el mercado**: es la tarifa que el bróker cobra por el
  acceso a cada mercado. El artículo 26.1 LIRPF permite deducir de los rendimientos del
  capital mobiliario, y solo, los gastos de administración y depósito de valores: lo que
  retribuye la custodia de los valores o la administración de las anotaciones en cuenta
  (V2117-19). La V0152-26 admite los gastos de mantenimiento de la cartera, pero no
  analiza esta tarifa y ninguna consulta leída la califica. Tampoco es un gasto
  inherente a la compra ni a la venta de un valor (art. 35 LIRPF), porque se cobra por
  el mercado y no por una operación. La herramienta no la deduce de la base y solo la
  resta de la rentabilidad neta. Si se dedujera, solo podría hacerse de los rendimientos
  del capital mobiliario del ejercicio. Para cerrarlo hace falta una consulta vinculante
  que califique la tarifa.
- **Abonos promocionales**: un abono que no devuelve gastos puede ser rendimiento del
  capital mobiliario, por la contraprestación de una cuenta (art. 25.2.a.2.º LIRPF), o
  ganancia patrimonial de la renta general (arts. 33.1, 37.1.l y 45 LIRPF). La
  herramienta no lo integra en ninguna base, lo muestra aparte y avisa. Para cerrarlo
  hace falta saber qué retribuye cada promoción.
- **Orden de las unidades de divisa**: la DGT fija que el valor de adquisición es el
  tipo al que se compró la divisa (V1613-25), pero no qué unidades se transmiten primero
  cuando hay varias compras. La herramienta las casa por orden de antigüedad, por
  analogía con el artículo 37.2 LIRPF.
- **Tope del convenio en países distintos de Estados Unidos**: la herramienta aplica el
  15 por ciento a todos los países. Es el tipo habitual de los convenios españoles sobre
  dividendos de cartera, pero no se ha comprobado país a país, y el informe nombra cada
  país en que se ha usado sin verificar.
- **Venta de unidades recompradas en una operación no definitiva**: el Manual práctico
  de Renta no fija cuándo se integra la pérdida diferida. Las consultas tratan la venta
  no definitiva que no libera pérdidas (V0571-21), pero no el destino de las unidades
  recompradas que se venden en ella. La herramienta deja la pérdida pendiente sin
  unidades y avisa.
- **Compras el mismo día**: el artículo 33.5.f habla de una «operación de compra», sin
  definirla. La herramienta cuenta las compras por fecha distinta, y no como una única
  operación.
- **Mercados fuera de la lista de equivalencia**: la V0778-25 cubre Nasdaq, NYSE y NYSE
  MKT. Un valor que solo cotiza en un mercado canadiense no tiene consulta. La
  herramienta aplica el plazo de dos meses a todos los valores.
- **Recuento en activos financieros**: el artículo 25.2.b contiene la misma regla de los
  dos meses que el 33.5.f, pero ninguna consulta leída aplica su recuento a un activo
  financiero. La herramienta usa el del artículo 33.5.f. La V0267-25 solo califica el
  ETC como activo financiero. Para el ETP del ejemplo no existe consulta.
- **Promoción de reembolso de comisiones**: un abono por comisiones ya pagadas puede
  considerarse menor gasto de las operaciones (arts. 35.1.b y 35.2 LIRPF) o ganancia
  patrimonial (art. 37.1.l LIRPF). La herramienta lo resta de los costes más antiguos y
  avisa. Para cerrarlo hace falta una confirmación escrita del bróker sobre la
  naturaleza del abono y, si no basta, una consulta a la DGT.
- **Valores de un bróker extranjero en el modelo 720**: la herramienta supone que están
  situados en el extranjero. La normativa no lo define expresamente.

## Límites de los datos

La herramienta solo ve un extracto. No conoce las operaciones realizadas en otros
brokers, que el artículo 33.5.f atribuye al contribuyente y no a la cuenta. Tampoco
conoce el valor de mercado a 31 de diciembre ni las pérdidas de ejercicios anteriores.
