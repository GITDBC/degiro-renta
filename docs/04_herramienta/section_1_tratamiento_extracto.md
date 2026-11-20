---
icon: lucide/table
title: Tratamiento del extracto
description:
    Qué hace la herramienta con cada concepto del extracto de Degiro, con la norma que
    lo respalda, y los avisos que emite cuando no puede calcular algo.
---

Esta página reúne, concepto por concepto, cómo trata la herramienta el extracto de
_Estado de cuenta_ de Degiro y en qué página de esta documentación está su fundamento.
Sirve para comprobar que el informe sigue la normativa descrita y para saber qué queda
fuera.

## Bibliografía

- Ley 35/2006, de 28 de noviembre, del Impuesto sobre la Renta de las Personas Físicas,
  arts. 14, 25, 26, 33, 35, 37, 49, 66, 76, 80, 99 y 103.
  [BOE](https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764).
- Las consultas vinculantes de la DGT que respaldan cada criterio se citan en la página
  enlazada de cada fila.

## Operaciones de valores

| Concepto del extracto                 | Tratamiento                                                                                                                                                                | Fundamento                                                                 |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Compra y venta                        | Se casan por FIFO y por ISIN con todo el historial del extracto, aunque el informe sea de un solo ejercicio.                                                               | [Ganancias y pérdidas](../01_renta_ahorro/section_2_ganancias_perdidas.md) |
| Costes, tasas e impuestos de la orden | Suman al valor de adquisición en las compras y restan del valor de transmisión en las ventas. Con ejecuciones parciales, se reparten por número de títulos.                | [Ganancias y pérdidas](../01_renta_ahorro/section_2_ganancias_perdidas.md) |
| Importe de la orden                   | En euros, el importe de la fila. En divisa, el contravalor en euros que el bróker cargó o abonó en el cambio de divisa de la orden.                                        | [Divisas](../01_renta_ahorro/section_4_divisas.md)                         |
| Orden en divisa sin cambio asociado   | No se puede valorar en euros. Se excluye del informe todo el historial de ese ISIN y se avisa.                                                                             | [Divisas](../01_renta_ahorro/section_4_divisas.md)                         |
| Operación sin número de orden         | Se trata como compra o venta y se avisa, porque Degiro anota así los cambios de ISIN, los _splits_ y los canjes, que normalmente no son una transmisión.                   | [Ganancias y pérdidas](../01_renta_ahorro/section_2_ganancias_perdidas.md) |
| Cantidad no entera                    | No se incluye en el informe. Se registra como error.                                                                                                                       | La herramienta trabaja con títulos enteros.                                |
| Pérdida con recompra en dos meses     | Se difiere según los criterios de la DGT y se integra al transmitir de forma definitiva. Se avisa de lo que sigue pendiente y de las ventas cuyo plazo supera el extracto. | [Regla de los dos meses](../01_renta_ahorro/section_3_regla_dos_meses.md)  |
| Valores de deuda                      | Su resultado va a rendimientos del capital mobiliario y no a ganancias patrimoniales. Solo se reconocen los ISIN de una lista cerrada, que hoy tiene uno.                  | [Rendimientos](../01_renta_ahorro/section_5_rendimientos.md)               |

## Dividendos, intereses y otros abonos

| Concepto del extracto              | Tratamiento                                                                                                                                              | Fundamento                                                                 |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Dividendo                          | Rendimiento del capital mobiliario por su importe bruto. En divisa, se convierte con el tipo implícito del cambio de divisa de la liquidación.           | [Rendimientos](../01_renta_ahorro/section_5_rendimientos.md)               |
| Dividendo en divisa sin cambio     | Se excluye con aviso, porque no hay tipo con que convertirlo.                                                                                            | [Cuestiones abiertas](../03_cuestiones_abiertas/section_1_fundamentals.md) |
| Retención del dividendo            | Con ISIN español es pago a cuenta. Con otro ISIN va a la deducción por doble imposición, con el tope del convenio. Una retención sin dividendo se avisa. | [Base del ahorro](../01_renta_ahorro/section_1_fundamentals.md)            |
| Intereses acreditados              | Rendimiento del capital mobiliario del artículo 25.2.                                                                                                    | [Rendimientos](../01_renta_ahorro/section_5_rendimientos.md)               |
| Intereses deudores                 | No se deducen de ninguna base. Solo reducen la rentabilidad neta.                                                                                        | [Rendimientos](../01_renta_ahorro/section_5_rendimientos.md)               |
| Comisión de conectividad           | No se deduce de la base. Solo reduce la rentabilidad neta.                                                                                               | [Cuestiones abiertas](../03_cuestiones_abiertas/section_1_fundamentals.md) |
| Reembolso de comisiones            | Se resta de los costes de transacción más antiguos que repaga, con aviso. Lo que sobra va a otros abonos.                                                | [Cuestiones abiertas](../03_cuestiones_abiertas/section_1_fundamentals.md) |
| Otras promociones y bonificaciones | No se integran en ninguna base. Se muestran aparte con un aviso.                                                                                         | [Rendimientos](../01_renta_ahorro/section_5_rendimientos.md)               |
| Cambio de divisa sin operación     | Ganancia o pérdida patrimonial, casando las unidades por FIFO. Sin compra previa en el extracto, no se calcula y se avisa.                               | [Divisas](../01_renta_ahorro/section_4_divisas.md)                         |
| Ingresos, retiradas y _Cash Sweep_ | No alteran el patrimonio. No entran en ninguna base.                                                                                                     | Sin efecto fiscal.                                                         |
| Fila no reconocida                 | Queda fuera del informe y se avisa con la descripción. Puede indicar un extracto en otro idioma o un movimiento nuevo.                                   | Sin efecto fiscal hasta que se clasifique.                                 |

## Cálculo del ejercicio

La herramienta integra todos los ejercicios desde el primero con actividad hasta el
pedido. Así llegan al pedido los saldos negativos de los cuatro años anteriores, con el
orden descrito en la [base del ahorro](../01_renta_ahorro/section_1_fundamentals.md). La
cuota aplica a la base la escala vigente desde 2025 a todos los ejercicios, sin mínimo
personal y familiar, y resta la deducción por doble imposición y las retenciones
españolas. Es una estimación, no la liquidación.

La rentabilidad neta real resta a ese resultado la cuota, las retenciones extranjeras no
recuperadas, la comisión de conectividad y los intereses deudores.

## Lo que no hace

- No aplica la regla de un año a las pérdidas por tipo de cambio.
- No calcula la base general, las deducciones, las pérdidas de ejercicios anteriores que
  no consten en el extracto ni las operaciones de otros bróker.
- No consulta ningún servicio externo. El tipo de cambio y los importes salen del
  extracto.
