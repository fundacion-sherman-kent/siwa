# Recorte de América Latina y el Caribe del Global Terrorism Index 2026

**Qué es.** Las filas de los 23 Estados del padrón de 33 que cubre el archivo
`GTI_PublicReleaseData_2026.xlsx` (hoja «Data»), edición 2026 del **Global
Terrorism Index** del **Institute for Economics & Peace (IEP)**, serie 2011–2025.
De las nueve columnas originales se conservan ocho: `iso3c`, `country`, `year`,
`rank`, `score`, `incidents`, `fatalities`, `injuries`, `hostages`. Se descarta
la fila 1 (aviso de copyright) y las filas de encabezado repetido; el resto de
los 163 países del mundo **no se copia a este repositorio**, porque el registro
solo publica los 23 Estados de América Latina y el Caribe que trae la fuente.

**Por qué el recorte y no el archivo entero.** El XLSX original lleva datos de
163 países: committear el archivo completo redistribuiría a este repositorio
público un conjunto mucho más amplio del que SIWA usa y del que el IEP
autorizó para este registro. El mismo criterio que ya rige para el Servicio
Geológico de los Estados Unidos (`fijas/usgs-mcs2026/`, que solo guarda las
filas mundiales que el colector consume) se aplica acá: se guarda **solo lo
que el colector `colectores/gti.py` lee**, en un formato (CSV) más liviano y
más fácil de auditar en un diff que el XLSX original.

**Cita.** Institute for Economics & Peace, *Global Terrorism Index 2026:
Measuring the Impact of Terrorism*, Sídney, 2026. https://www.economicsandpeace.org/

**Licencia.** Creative Commons Atribución-NoComercial-CompartirIgual 4.0
Internacional (**CC BY-NC-SA 4.0**), con atribución obligatoria al IEP. **No
comercial**: este dato solo puede viajar en el registro público y gratuito de
SIWA, nunca en un producto que la Fundación cobre, sin gestionar antes una
licencia distinta con el IEP. Ver `colectores/comun.py`, diccionario
`RESTRICCIONES`, clave `gti_iep_no_comercial`.

**Por qué es file-drop y no se automatiza.** El archivo no tiene descarga
directa: el IEP lo entrega por licencia, a pedido, mediante un formulario de
solicitud (`economicsandpeace.org/consulting/data-licensing`) — verificado en
vivo el 21/9/2026 por `colectores/owd.py`, que dejó la gestión pendiente. La
Dirección tramitó esa licencia y bajó el archivo a mano el 21/9/2026. El
colector **no intenta ninguna descarga en línea**: lee este recorte, que es
la única puerta que existe.

**Cobertura.** 23 de los 33 Estados del padrón. **Faltan 10, y el GTI no los
incluye**: Antigua y Barbuda (ATG), Bahamas (BHS), Belice (BLZ), Barbados
(BRB), Dominica (DMA), Granada (GRD), San Cristóbal y Nieves (KNA), Santa
Lucía (LCA), San Vicente y las Granadinas (VCT) y Surinam (SUR). No aparecer
no es lo mismo que no tener: el IEP no codifica a los micro-Estados del Caribe
oriental en esta edición.

**Cuándo se reemplaza.** Cuando el IEP publique la edición siguiente (marzo de
cada año, habitualmente) y la Dirección gestione y descargue el nuevo archivo
con la misma licencia. El reloj de actualidad (`herramientas/reloj-actualidad.py`)
avisa cuando el dato queda desactualizado frente a la fuente.
