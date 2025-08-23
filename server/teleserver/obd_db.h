//#pragma once
#ifndef __OBD_DB_H__
#define __OBD_DB_H__

#include "teleserver.h"
#ifdef POSTGRES_DB
#include <libpq-fe.h>
#endif


PGconn* connDb();
//int dbInsert(CHANNEL_DATA* pld, char* payload);

int InsertOBDMaster(CHANNEL_DATA* pld, char* payload);
#endif // __OBD_DB_H__