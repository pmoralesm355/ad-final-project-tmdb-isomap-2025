Instalación




Python 3.x


pip install -r requirements.txt




Parte 1 – Grafo TMDB




Configurar API Key TMDB en .env.


Ejecutar: python part1_tmdb/build_graph.py


Genera CSV de nodos/aristas y visualización del grafo de colaboraciones de Samuel L. Jackson.




Parte 2 – SQLite + BI




Ejecutar: python part2_db/load_to_sqlite.py


Crea ad_final.db con tablas incidents, details, outcomes y vistas:


v_pct_incidents_2018_2020


v_top3_transport_intelligence


v_detection_avg_arrested


v_category_max_prison_days


v_yearly_fines




Conectar ad_final.db vía ODBC a Power BI para las 5 visualizaciones.




Parte 3 – ISOMAP




Colocar isomap.dat en la raíz del proyecto.


Ejecutar: python part3_isomap/isomap.py


Implementación propia de ISOMAP (sin sklearn) y guardado de plots/isomap_faces_embedding.png.

