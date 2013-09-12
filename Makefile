all:
	mkdir -p build
	cd build && cmake ../libfab && make && make install

install: all
	cp -rf kokopelli koko /usr/local/bin/
	cp -rf libfab/libfab.* /usr/local/lib/
	if which ldconfig; then ldconfig; fi

clean:
	rm -rf build
