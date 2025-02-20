#!/usr/bin/python3

import serial
import Serial_config
import paho.mqtt.client as mqtt
import json
import threading
import time

class Vallox:
	def __init__(self, client, topic, serial_port, logger):
		self._logger = logger

		# Connect to MQTT broker
		self.client = client
		self.topic = topic
		self._logger.info("Successfully connected to MQTT broker!")

		# Init serial connection
		self.port = serial.Serial(serial_port, baudrate=9600)
		self._logger.info("Serial port initialized!")

		self.vallox_data = {}
		self.counter = 0


	def read_byte(self):
		return self.port.read()

	def process_measurement(self, identifier, value):
		self.vallox_data.update({identifier: value})
		# Publish for only every 25th measurement
		# TODO publish when every value is updated
		if self.counter == 25:
			self._logger.info(f"Publishing {self.vallox_data} to {self.topic}")
			self.client.publish(self.topic, str(json.dumps(self.vallox_data)))
			self.counter = 0
		self.counter += 1

	def process_sentence(self, sentence):
		sender = sentence[1]
		recipient = sentence[2]
		valuetype = sentence[3]
		value = sentence[4]
		checksum = sentence[5]

		self._logger.info(f"Received sentence from {sender} to {recipient} (valuetype={valuetype}, value={value}).")
		if sender in Serial_config.SENTENCE_SYSTEM:
			# Only process sentences originating from controller
			if valuetype in Serial_config.TEMP_IDENTIFIERS:
				self.process_measurement(Serial_config.TEMP_IDENTIFIERS[valuetype], Serial_config.TEMP_LOOKUP[value])
			elif valuetype == Serial_config.TYPE_FANSPEED:
				self.process_measurement("FANSPEED", Serial_config.FANSPEED_LOOKUP[value])
			elif valuetype == Serial_config.TYPE_RH1:
				self.process_measurement("RH1", self.valueToRh(value))
			elif valuetype == Serial_config.TYPE_RH2:
				self.process_measurement("RH2", self.valueToRh(value))

	def valueToRh(self, value):
		if value < 51:
			return None
		return int((value - 51) / 2.04)

	def monitor_values(self):
		self._logger.info("Starting monitoring Vallox readings!!")
		sentence = bytearray()
		while True:
			sentence += self.read_byte()
			length = len(sentence)
			if (
				(length == 1 and (sentence[-1] not in Serial_config.SENTENCE_START)) or
				((length == 2 or length == 3) and sentence[-1] not in Serial_config.SENTENCE_VALID_PEERS)
			):
				# TODO: Handle bytes. Eventually valid values are there with an offset, do not just throw them away
				#self._logger.info(f"Input discarded")
				sentence = bytearray()
			elif length >= 6:
				# sentence valid: correct start byte, syntactically correct sender and recipient
				self.process_sentence(sentence)
				sentence = bytearray()

	def on_message(self, client, userdata, message):
		self.change_fan_speed(str(message.payload.decode("utf-8")))

	def subscribe(self):
		self._logger.info(f"Started subscribing topic {self.topic}/control")
		self.client.on_message = self.on_message
		self.client.subscribe(f"{self.topic}/control")

	def change_fan_speed(self, value):
		self._logger.info(f"Setting fanspeed to {value}")
		self.port.write(Serial_config.FANSPEED_SET[value])


if __name__ == "__main__":
	client = mqtt.Client()
	self.client.username_pw_set(username, password)
	vallox = Vallox(client, MQTT_config.topic, Serial_config.SERIAL_PORT, logger)
	#vallox.subscribe()
	monitor = threading.Thread(target=vallox.monitor_values)
	monitor.start()
