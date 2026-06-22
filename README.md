# **SIGMA: Smart Interventive Greenhouse Monitoring and Actuation**

### Integrantes

|Nombres|Github|Correos|
|-|-|-|
|Oliver Peñailillo|[@pyrrss](https://www.github.com/pyrrss)|openailillo2023@udec.cl|
|Manuel Isaac|[@sshiro0](https://www.github.com/sshiro0)|francnunez2023@udec.cl|
|Javier Campos|[@4lehh](https://www.github.com/4lehh)|jacampos2023@udec.cl|
|Juan Felipe Raysz|[@Sephir0ath](https://www.github.com/Sephir0ath)|jraysz2023@udec.cl|
|Matías García|[@Matygp](https://www.github.com/Matygp)|matgarcia2023@udec.cl|

### Tecnologias

<div align="center">

<a href="https://skillicons.dev">
  <img src="https://skillicons.dev/icons?i=python,git,github,vscode,docker&perline=5" />
</a>

</div>

### Descripción del proyecto

**SIGMA** (Smart Interventive Greenhouse Monitoring and Actuation) es un sistema ciberfísico simulado de monitoreo ambiental remoto diseñado para entornos críticos, específicamente enfocado en la supervisión inteligente de invernaderos. 

El sistema aborda directamente la falta de visibilidad en tiempo real y la ausencia de mecanismos automatizados de respuesta remota ante variables ambientales descontroladas (como humedad, temperatura y radiación solar), factores que pueden provocar consecuencias devastadoras como incendios o la pérdida total de los cultivos. 

A través de una arquitectura centralizada cliente-servidor desarrollada completamente en software, SIGMA captura de forma constante los datos obtenidos por nodos sensores distribuidos. Al detectar el traspaso de umbrales críticos preestablecidos, el servidor activa de manera autónoma nodos actuadores para mitigar los riesgos y estabilizar el entorno de forma oportuna.

### Ejecución

>[!IMPORTANT]
>Se requiere tener Docker 29.0.0 en adelante.  

Para montar el proyecto, hemos utilizado Docker Compose. Para la ejecución del código, siga los siguientes pasos.

```sh
# Levantar el proyecto
sudo docker compose up --build

# Ver los logs del server o del sensor. (prints de python)
sudo docker compose logs -f server/sensor 

# Apagar el proyecto
sudo docker compose down
```