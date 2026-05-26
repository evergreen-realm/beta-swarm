/* eslint-disable no-unused-vars, no-undef */
describe('APIClient', () => {
  let client;

  beforeEach(() => {
    client = new APIClient('https://example.com/api');
  });

  it('lists all available endpoints', () => {
    return client.listEndpoints().then((endpoints) => {
      expect(endpoints).toBeInstanceOf(Object);
    });
  });

  it('lists all available sensors', () => {
    return client.listSensors().then((sensors) => {
      expect(sensors).toBeInstanceOf(Object);
    });
  });

  it('creates a new reading for the specified sensor', () => {
    const data = {
      sensorId: 1,
      value: 42,
    };

    return client.createReading(data).then((reading) => {
      expect(reading).toBeInstanceOf(Object);
    });
  });

  it('retrieves a reading by ID', () => {
    const id = 1;

    return client.getReading(id).then((reading) => {
      expect(reading).toBeInstanceOf(Object);
    });
  });

  it('updates a reading by ID', () => {
    const id = 1;
    const data = {
      value: 24,
    };

    return client.updateReading(id, data).then((reading) => {
      expect(reading).toBeInstanceOf(Object);
    });
  });

  it('deletes a reading by ID', () => {
    const id = 1;

    return client.deleteReading(id).then(() => {
      expect(true).toBe(true);
    });
  });

  it('lists all available readings for the specified sensor', () => {
    const sensorId = 1;

    return client.listReadingsForSensor(sensorId).then((readings) => {
      expect(readings).toBeInstanceOf(Object);
    });
  });

  it('lists all available sensors for the specified category', () => {
    const category = 'temperature';

    return client.listSensorsByCategory(category).then((sensors) => {
      expect(sensors).toBeInstanceOf(Object);
    });
  });

  it('retrieves a sensor by ID', () => {
    const id = 1;

    return client.getSensor(id).then((sensor) => {
      expect(sensor).toBeInstanceOf(Object);
    });
  });

  it('updates a sensor by ID', () => {
    const id = 1;
    const data = {
      name: 'New sensor name',
    };

    return client.updateSensor(id, data).then((sensor) => {
      expect(sensor).toBeInstanceOf(Object);
    });
  });

  it('deletes a sensor by ID', () => {
    const id = 1;

    return client.deleteSensor(id).then(() => {
      expect(true).toBe(true);
    });
  });
});