.result_touched: draw_vis.py
	python ./draw_vis.py
	touch .result_touched

%.svg: .result_touched ;

%.png: %.svg
	npx svgexport $< $@ "svg{background:#f8f8ff;}"

all: result_africa.svg result_asia.svg result_europe.svg result_north_america.svg result_oce.svg result_south_america.svg result_usa.svg result_world.svg \
     result_africa.png result_asia.png result_europe.png result_north_america.png result_oce.png result_south_america.png result_usa.png result_world.png ;

.DEFAULT_GOAL := all
.PHONY: all
