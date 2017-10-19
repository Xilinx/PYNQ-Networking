CC=gcc
CC_FLAGS=-shared -fPIC

packetSlurper.so: packet_slurper.c
	$(CC) $(CC_FLAGS) $< -o $@

clean:
	rm -rf *.so
