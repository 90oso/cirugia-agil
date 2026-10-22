# Evaluación comercial y arquitectura objetivo — Cirugía Ágil

## Veredicto
**Oportunidad: alta en nicho. Riesgo: alto. No apto aún para producción con datos clínicos reales.**
Cliente a investigar: aseguradora, administradora de beneficios o equipo de preautorizaciones de hospitales. Comprador: jefe de operaciones/siniestros. Usuarios: analistas y supervisores médicos/administrativos.

## Lo que hay en el repositorio
- Lectura de informes y evidencia estructurada, reglas deterministas, historial y exportación; integración Gemini y Notion original.
- Nueva capa `app/catalog.py`: catálogo local SQLite con paciente, póliza, plan y coberturas. Se configura como backend predeterminado en esta rama; Notion queda como compatibilidad opcional.
- Demo `docs/index.html`: simulador **sin API, sin IA externa y sin datos clínicos** con carencia, vigencia, exclusiones por plan, faltantes, expediente exportable.

## Flujo profesional propuesto
1. Administrador parametriza planes, versiones de cobertura, exclusiones y documentos en la plataforma (no en Notion).
2. Operaciones registra solicitud, póliza y documentos; validación de formato y carga segura.
3. Extracción de hechos por IA con origen verificable; revisión de correspondencia paciente/póliza.
4. Motor de reglas versionado explica cada chequeo; si hay incertidumbre, abstiene y escala.
5. Analista autoriza, solicita correcciones o rechaza manualmente con justificación; historial inmutable de cambios.
6. Supervisión: métricas, trazabilidad, exportación y conectores hospital/aseguradora.

## Arquitectura objetivo
Web responsiva + FastAPI + PostgreSQL (separación por cliente/empresa) + almacenamiento seguro de documentos (control de acceso y cifrado) + cola para procesamiento IA + auditoría + SSO/MFA + backups y observabilidad. 
**SQLite solo para desarrollo/piloto aislado.** No enviar documentos reales a proveedores IA sin acuerdos y base legal aplicable.

## Bloqueos previos a vender
- Autenticación fuerte, autorización en cada endpoint, segregación por empresa y revisión de permisos sobre expedientes.
- Gestión segura de datos de salud y sus ciclos de vida; revisión legal y contractual según Ley 81/2019 y Decreto 285/2021 en Panamá.
- Validación contra procedimientos reales mediante un experto médico/seguros, matriz de errores falsos positivos/negativos y abstención segura.
- Definir quién tiene autoridad para preaprobar. La IA no decide por el asegurador ni garantiza elegibilidad.
- Tests de integración y evaluación con conjuntos ficticios, luego datos anonimizados con acuerdos.
- Catálogo editable desde UI corporativa, gestión de versiones y migración a PostgreSQL.

## Experimento de mercado
Entrevistar a operadores de preautorización: número de casos por mes, tiempos por expediente, motivos de devolución, costo de errores, integraciones obligatorias. Ofrecer piloto con documentos ficticios primero. KPI principal: minutos de revisión manual por expediente manteniendo tasa de errores controlada.

## Criterios de demo
- Póliza activa y documentación completa -> resultado preliminar.
- Falta de documentos -> listado concreto.
- Procedimiento no cubierto y póliza vencida -> estado justificable.
- Exportación con información ficticia, sin exponer datos sensibles.

**Fuente regulatoria:** https://antai.gob.pa/preguntas-frecuentes-de-proteccion-de-datos-personales/ ; https://antai.gob.pa/reglamentan-ley-81-de-proteccion-de-datos-personales/
