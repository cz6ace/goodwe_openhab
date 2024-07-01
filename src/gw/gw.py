import argparse
import asyncio
import sys
import goodwe
import paho.mqtt.client as mqtt
VERSION="0.0.3"

def kind_to_str(kind):
    if kind is None:
        return "NA"
    return kind.name

        
async def get_runtime_data(ip_address):
    inverter = await goodwe.connect(ip_address)
    runtime_data = await inverter.read_runtime_data()

    for sensor in inverter.sensors():
        if sensor.id_ in runtime_data:
            print(f"{sensor.id_}: \t\t {sensor.name} = {runtime_data[sensor.id_]} {sensor.unit}")


async def run_mqtt(ip_address, mqtt_host, topic, delay, tries=100):
    client = mqtt.Client()
    client.connect(mqtt_host, 1883, 60)
    client.loop_start()
    # wait for mqtt
    await asyncio.sleep(3)
    cntr = tries
    # give just two chances to connect to goodwe and then just in a loop
    # read the runtime data to reduce the traffic
    try:
        inverter = await goodwe.connect(ip_address)
    except Exception as e:
        await asyncio.sleep(3)
        inverter = await goodwe.connect(ip_address)

    while True:
        try:
            runtime_data = await inverter.read_runtime_data()
            print("data successfully read")
        except Exception as e:
            print("Error reading from GoodWe", e)
            cntr -= 1
            if not cntr:
                return 1
            await asyncio.sleep(delay / 3)
            continue
        cntr = tries

        any_data_sent = False
        for sensor in inverter.sensors():
            if sensor.id_ in runtime_data:
                print(f"{sensor.id_}: \t\t {sensor.name} = {runtime_data[sensor.id_]} {sensor.unit}")
                value = str(runtime_data[sensor.id_])
                if "timestamp" in sensor.id_:
                    value = value.replace(' ', 'T')
                client.publish(f"{topic}/{sensor.id_}", value)
                any_data_sent = True
        if not any_data_sent:
            print("No data in runtime? Nothing published")
        await asyncio.sleep(delay)


async def get_items(ip_address, topic, groups="gSolar", camel_case=True, prefix="Solar"):
    inverter = await goodwe.connect(ip_address)
    for group in groups.split(","):
        print(f"Group {group}")
    for sensor in inverter.sensors():
        if "_label" in sensor.id_ or "errors" in sensor.id_ or "_warning" in sensor.id_ or "_error" in sensor.id_:
            sensor_type = "String"
        elif "timestamp" in sensor.id_:
            sensor_type = "DateTime"
        else:
            sensor_type="Number"
        unit_str = ""
        format_str = "%.1f"
        icon_str = ""
        if sensor.unit:
            if sensor.unit == "%":
                unit_str = " [%%]"
            else:
                unit_str=f" [{sensor.unit}]"
            if sensor.unit in ["W", "VA"]:
                icon_str = "<energy>"
        if sensor.id_.endswith("stamp"):
            format_str = "%1$ta %1$tR"
        item_name = prefix + sensor.id_
        if camel_case:
            item_name = item_name.title() 
        unit_str = ""
        if sensor.unit:
            unit_str=f" [{sensor.unit}]"
        print(f"{sensor_type} {item_name} \"{sensor.name} [{format_str}{unit_str}]\" {icon_str} ({groups}) {{ channel=\"mqtt:topic:mq:solar:{sensor.id_}\" }}")


async def get_thing(ip_address, topic):
    inverter = await goodwe.connect(ip_address)
    print("""
Thing mqtt:topic:mq:solar "Solar" (mqtt:broker:mq) @ "roof" {
    Channels:
""")
    for sensor in inverter.sensors():
        if "_label" in sensor.id_ or "errors" in sensor.id_ or "_warning" in sensor.id_ or "_error" in sensor.id_:
            sensor_type = "string"
        elif "timestamp" in sensor.id_:
            sensor_type = "datetime"
        else:
            sensor_type="number"
        unit_str = ""
        if sensor.unit:
            unit_str=f" [{sensor.unit}]"
        #id={sensor.id_} name={sensor.name} unit={sensor.unit} kind={kind_to_str(sensor.kind)}
        print(f"""        Type {sensor_type} : {sensor.id_} "{sensor.name}{unit_str}" [ stateTopic="{topic}/{sensor.id_}" ]""")
    print("""}""")


def main():
    parser = argparse.ArgumentParser(description='GoodWe app')
    parser.add_argument("--host", action="store", dest="host", default="192.168.2.92")
    parser.add_argument("-i", "--items", action="store_true", dest="items")
    parser.add_argument("--groups", action="store", dest="groups", default="gSolar")
    parser.add_argument("--prefix", action="store", dest="prefix", default="solar_")
    parser.add_argument("--camel-case", action="store_true", dest="camel_case")
    parser.add_argument("-t", "--thing", action="store_true", dest="thing")
    parser.add_argument("--topic", action="store", dest="topic", default="solar")
    parser.add_argument("-r", "--run", action="store_true", dest="run")
    parser.add_argument("--mqtt", action="store", dest="mqtt", default="localhost")
    parser.add_argument("--delay", action="store", dest="delay", default=15, type=int)
    parser.add_argument("--version", action="version", version=VERSION)

    args = parser.parse_args()

    if args.run:
        code = asyncio.run(run_mqtt(args.host, args.mqtt, args.topic, args.delay))
        sys.exit(code)
    elif args.items:
        asyncio.run(get_items(args.host, args.topic, args.groups, args.camel_case, args.prefix))
    elif args.thing:
        asyncio.run(get_thing(args.host, args.topic))
    else:
        asyncio.run(get_runtime_data(args.host))

if __name__ == "__main__":    
  main()

