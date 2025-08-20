#include "obd_db.h"

#ifdef POSTGRES_DB
#include <libpq-fe.h>
PGconn* conn;
#endif  //POSTGRES_DB


PGconn* connDb()
{
	const char* conninfo = "host=localhost dbname=kiapi_db user=kiapicav password='confi11' ";
	/* 연결 열기 */
	conn = PQconnectdb(conninfo);
	if (PQstatus(conn) != CONNECTION_OK) {
		fprintf(stderr, "Connection to database failed : % s", PQerrorMessage(conn));
		PQfinish(conn);
		return conn;
	}
	return conn;
}

int InsertMaster(unsigned char gatr_scn, char* vin, char* payload, uint32_t ts)
{
	PGresult* res;
	if (!conn)
	{
		char sql[256];
		conn=connDb();
		sprintf(sql, "insert into tbl_obd_data_master(gatr_scn, vin, data_gatr_expl, rgst_dtm) values (%d, '%s', '%s', %ld);", 
			gatr_scn, vin, payload, ts);
		printf("SQL: %s]n", sql);
		/* 쿼리문 실행 */
		res = PQexec(conn, sql);
		if (PQresultStatus(res) != PGRES_TUPLES_OK) {
			fprintf(stderr,"Query failed : %s", PQerrorMessage(conn));
			PQclear(res);
			PQfinish(conn);
			return -1;
		}
		return 0;
	}
	else
	{
		fprintf(stderr, "Please check the DB connection\n");
		return -1;
	}
}