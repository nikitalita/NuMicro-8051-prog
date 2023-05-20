CC = gcc
CFLAGS = -g -Wall

#LDFLAGS = -lgpiod
DEV_OBJ = stub.o

default: all

all: nuvoicp shared
nuvoicp: main.o icp.o $(DEV_OBJ)
	$(CC) $(CFLAGS) -o nuvoicp $^ $(LDFLAGS)
shared: main.o icp.o $(DEV_OBJ)
	$(CC) $(CFLAGS) -shared -o libnuvoicp.so $^ $(LDFLAGS)
	mv libnuvoicp.so ../nuvoispy/
clean:
	rm -f nuvoicp *.o
	rm -f ../nuvoispy/libnuvoicp.so