#pragma once
#ifndef __OBD_DB_H__
#define __OBD_DB_H__
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <stdint.h>
#include <ctype.h>
#include <errno.h>
#include <sys/stat.h>
#include "data2kml.h"
#include "httpd.h"
#include "teleserver.h"
#include "logdata.h"
#include "processpil.h"
#include "revision.h"

#ifdef POSTGRES_DB
#include <libpq-fe.h>
#endif


PGconn* connDb();

#endif // __OBD_DB_H__