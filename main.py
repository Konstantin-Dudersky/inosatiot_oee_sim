import sys
from datetime import datetime, timedelta

import yaml
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from loguru import logger

from machine import Machine


def check_bucket(client: InfluxDBClient, bucket_name: str):
    try:
        bucket = client.buckets_api().find_bucket_by_name(bucket_name)
    except Exception as e:
        logger.critical(e)
        sys.exit(1)

    if bucket is None:
        logger.warning(f"bucket {bucket_name} in host {client.url} not found")
        bucket = client.buckets_api().create_bucket(bucket_name=bucket_name)
        logger.success(f"bucket {bucket.name} in host {client.url} created")


if __name__ == '__main__':
    stop = datetime.now().astimezone()
    start = stop - timedelta(days=30)

    logger.info(f"start simulation from {start.isoformat()} to {stop.isoformat()}")

    machines = []
    with open('config.yaml') as stream:
        config = yaml.safe_load(stream)

        for m in config['machines']:
            machines.append(Machine(
                now=start,
                config=m['params'],
                name=m['name'])
            )

    client = InfluxDBClient(
        url=config['influxdb']['url'],
        token=config['influxdb']['token'],
        org=config['influxdb']['org'],
    )

    client.buckets_api().delete_bucket(client.buckets_api().find_bucket_by_name(config['influxdb']['bucket']))
    check_bucket(client=client, bucket_name=config['influxdb']['bucket'])
    write_api = client.write_api(write_options=SYNCHRONOUS)

    now = start
    period = 10
    while True:
        # progress_bar((batch_ts - start).total_seconds(), (stop - start).total_seconds(), bar_length=50)

        record = []
        for i in range(1000):
            for m in machines:
                record.extend(m.cycle(now))

            now += timedelta(seconds=period)
            if now >= stop:
                break

        write_api.write(
            bucket=config['influxdb']['bucket'],
            record=record
        )

        if now >= stop:
            # progress_bar((batch_ts - start).total_seconds(), (stop - start).total_seconds(), bar_length=50)

            print("\nBatch execution finished")
            sys.exit()
