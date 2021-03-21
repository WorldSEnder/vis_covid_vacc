RESULT_SVGS := result_africa.svg\
               result_asia.svg\
			   result_europe.svg\
			   result_middle_east.svg\
			   result_north_america.svg\
			   result_oce.svg\
			   result_south_america.svg\
			   result_usa.svg\
			   result_world.svg
RESULT_PNGS := $(RESULT_SVGS:.svg=.png)

$(RESULT_SVGS) &: draw_vis.py .setup_done
	python ./draw_vis.py

%.png: %.svg .setup_done
	npx svgexport $< $@ "svg{background:#f8f8ff;}"

all: $(RESULT_SVGS) $(RESULT_PNGS) ;

update: .setup_done
	git submodule foreach --recursive git pull --ff-only

.setup_done:
	npm ci
	git submodule update --init --recursive
	touch .setup_done

setup: .setup_done ;

.DEFAULT_GOAL := all
.PHONY: all update
