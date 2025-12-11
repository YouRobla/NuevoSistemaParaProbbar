# 🔄 Ejemplo Completo: Múltiples Cambios de Habitación

## 📋 Escenario Completo

Imagina que tienes un huésped que:
1. **Reserva original:** 10/11/2024 - 15/11/2024 en Habitación 101
2. **Primer cambio:** El 12/11 se cambia a Habitación 102 hasta el 15/11
3. **Segundo cambio:** El 13/11 se cambia a Habitación 103 hasta el 16/11 (extiende estancia)

---

## 🎬 Paso 1: Reserva Original

### **Datos Iniciales:**

```javascript
// Reserva creada normalmente
const reservaOriginal = {
  id: 123,
  sequence_id: "RES-2024-001",
  partner_id: 100,
  hotel_id: 1,
  check_in: "2024-11-10 14:00:00",
  check_out: "2024-11-15 11:00:00",
  status_bar: "confirmed",
  rooms: [
    {
      id: 456,
      product_id: 10,  // Habitación 101
      name: "Habitación 101",
      booking_days: 5,
      price: 100.00
    }
  ]
};
```

**Estado:** 
- Habitación 101
- 10/11 14:00 → 15/11 11:00
- 5 noches

---

## 🔄 Paso 2: Primer Cambio de Habitación (12/11)

### **Situación:**
- Huésped quiere cambiar el **12/11** a Habitación 102
- Nueva habitación hasta el **15/11** (mismo check-out)

### **Código Frontend:**

```javascript
// Función helper
const applyRoomChange = async (bookingId, changeData) => {
  const payload = {
    booking_line_id: changeData.lineId,
    new_room_id: changeData.newRoomId,
    change_start_date: changeData.startDate,
    change_end_date: changeData.endDate,
    // Horas opcionales
    check_in_hour: changeData.startHour,
    check_in_minute: changeData.startMinute,
    check_out_hour: changeData.endHour,
    check_out_minute: changeData.endMinute,
    note: changeData.note || ''
  };

  // Remover campos null/undefined
  Object.keys(payload).forEach(key => {
    if (payload[key] === null || payload[key] === undefined) {
      delete payload[key];
    }
  });

  const response = await fetch(
    `https://tu-servidor.com/api/hotel/reserva/${bookingId}/change_room`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'tu-api-key'
      },
      body: JSON.stringify(payload)
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Error al aplicar cambio');
  }

  return await response.json();
};

// Aplicar primer cambio
try {
  const primerCambio = await applyRoomChange(123, {
    lineId: 456,              // ID de la línea de reserva original
    newRoomId: 11,            // Habitación 102
    startDate: "2024-11-12",  // Cambio desde el 12/11
    endDate: "2024-11-15",    // Hasta el 15/11 (mismo que original)
    startHour: 14,            // Check-in a las 14:00
    startMinute: 0,
    endHour: 11,              // Check-out a las 11:00
    endMinute: 0,
    note: "Primer cambio solicitado por el cliente"
  });

  console.log('✅ Primer cambio aplicado:', primerCambio);
} catch (error) {
  console.error('❌ Error:', error.message);
}
```

### **Payload Enviado:**

```json
{
  "booking_line_id": 456,
  "new_room_id": 11,
  "change_start_date": "2024-11-12",
  "change_end_date": "2024-11-15",
  "check_in_hour": 14,
  "check_in_minute": 0,
  "check_out_hour": 11,
  "check_out_minute": 0,
  "note": "Primer cambio solicitado por el cliente"
}
```

### **Validaciones que Hace el Backend:**

1. ✅ **Reserva existe:** Verifica que reserva 123 existe
2. ✅ **Línea existe:** Verifica que línea 456 pertenece a reserva 123
3. ✅ **Habitación diferente:** Verifica que habitación 11 ≠ 10
4. ✅ **Fechas válidas:** Verifica que 12/11 < 15/11
5. ✅ **Fecha inicio válida:** Verifica que 12/11 está entre 10/11 y 15/11
6. ✅ **Disponibilidad:** Verifica que habitación 11 está libre del 12/11 al 15/11
7. ✅ **Horas válidas:** Verifica que horas (0-23) y minutos (0-59) son válidos

### **Resultado del Backend:**

```javascript
// Respuesta del API
{
  "success": true,
  "message": "Cambio de habitación aplicado correctamente.",
  "data": {
    "reserva_id": 123,  // Reserva original (modificada)
    "new_reserva": {
      "id": 124,        // NUEVA reserva creada
      "sequence_id": "RES-2024-002",
      "check_in": "2024-11-12 14:00:00",
      "check_out": "2024-11-15 11:00:00",
      "check_in_hour": 14,
      "check_in_minute": 0,
      "check_out_hour": 11,
      "check_out_minute": 0,
      "status_bar": "checkin",
      "connected_booking_id": 123
    }
  }
}
```

### **Estado Después del Primer Cambio:**

```
┌─────────────────────────────────────────────────────┐
│ RESERVA ORIGINAL (ID: 123) - MODIFICADA            │
│ Habitación: 101                                     │
│ Check-in:  10/11 14:00                              │
│ Check-out: 12/11 11:00  ← Automático (antes era 15/11) │
│ Estado:    checkin                                  │
│ Noches:    2 noches                                 │
│ connected_booking_id: 124                           │
│ is_room_change_origin: true                         │
└─────────────────────────────────────────────────────┘
                        │
                        │
┌─────────────────────────────────────────────────────┐
│ NUEVA RESERVA (ID: 124) - CREADA                   │
│ Habitación: 102                                     │
│ Check-in:  12/11 14:00                              │
│ Check-out: 15/11 11:00                              │
│ Estado:    checkin                                  │
│ Noches:    3 noches                                 │
│ connected_booking_id: 123                           │
│ split_from_booking_id: 123                          │
│ is_room_change_destination: true                    │
└─────────────────────────────────────────────────────┘
```

---

## 🔄 Paso 3: Segundo Cambio de Habitación (13/11)

### **Situación:**
- Huésped quiere cambiar **desde la reserva 124** (habitación 102)
- Cambio el **13/11** a Habitación 103
- Nueva habitación hasta el **16/11** (extiende estancia)

### **Importante:**
Ahora trabajamos con la **reserva 124** (la creada en el primer cambio), NO con la original (123).

### **Código Frontend:**

```javascript
// Primero, obtener los datos actuales de la reserva 124
const obtenerReserva = async (reservaId) => {
  const response = await fetch(
    `https://tu-servidor.com/api/hotel/reservas/${reservaId}`,
    {
      headers: {
        'X-API-Key': 'tu-api-key'
      }
    }
  );
  return await response.json();
};

// Obtener datos de la reserva actual
const reservaActual = await obtenerReserva(124);
console.log('Reserva actual:', reservaActual.data);

// Aplicar segundo cambio desde la reserva 124
try {
  const segundoCambio = await applyRoomChange(124, {
    lineId: reservaActual.data.rooms[0].id,  // ID de la línea de la reserva 124
    newRoomId: 12,                            // Habitación 103
    startDate: "2024-11-13",                  // Cambio desde el 13/11
    endDate: "2024-11-16",                    // Hasta el 16/11 (EXTIENDE)
    startHour: 15,                            // Check-in a las 15:00 (diferente hora)
    startMinute: 30,
    endHour: 12,                              // Check-out a las 12:00
    endMinute: 0,
    note: "Segundo cambio y extensión de estancia"
  });

  console.log('✅ Segundo cambio aplicado:', segundoCambio);
} catch (error) {
  console.error('❌ Error:', error.message);
}
```

### **Payload Enviado:**

```json
{
  "booking_line_id": 789,  // ID de la línea de la reserva 124
  "new_room_id": 12,
  "change_start_date": "2024-11-13",
  "change_end_date": "2024-11-16",
  "check_in_hour": 15,
  "check_in_minute": 30,
  "check_out_hour": 12,
  "check_out_minute": 0,
  "note": "Segundo cambio y extensión de estancia"
}
```

### **Validaciones del Backend (Segundo Cambio):**

1. ✅ **Reserva existe:** Verifica que reserva 124 existe
2. ✅ **Línea existe:** Verifica que línea 789 pertenece a reserva 124
3. ✅ **Habitación diferente:** Verifica que habitación 12 ≠ 11 (habitación actual)
4. ✅ **Fechas válidas:** Verifica que 13/11 < 16/11
5. ✅ **Fecha inicio válida:** Verifica que 13/11 está entre 12/11 (check-in actual) y 15/11 (check-out actual)
6. ✅ **Disponibilidad:** Verifica que habitación 12 está libre del 13/11 al 16/11
7. ✅ **Extensión permitida:** Permite que 16/11 > 15/11 (extiende la estancia)
8. ✅ **Horas válidas:** Verifica horas y minutos

### **Resultado del Backend:**

```javascript
{
  "success": true,
  "message": "Cambio de habitación aplicado correctamente.",
  "data": {
    "reserva_id": 124,  // Reserva 124 (modificada)
    "new_reserva": {
      "id": 125,        // TERCERA reserva creada
      "sequence_id": "RES-2024-003",
      "check_in": "2024-11-13 15:30:00",
      "check_out": "2024-11-16 12:00:00",
      "check_in_hour": 15,
      "check_in_minute": 30,
      "check_out_hour": 12,
      "check_out_minute": 0,
      "status_bar": "checkin",
      "connected_booking_id": 124
    }
  }
}
```

### **Estado Final Después del Segundo Cambio:**

```
┌─────────────────────────────────────────────────────┐
│ RESERVA ORIGINAL (ID: 123)                          │
│ Habitación: 101                                     │
│ Check-in:  10/11 14:00                              │
│ Check-out: 12/11 11:00                              │
│ Estado:    checkin                                  │
│ connected_booking_id: 124                           │
│ is_room_change_origin: true                         │
└─────────────────────────────────────────────────────┘
                        │
                        │
┌─────────────────────────────────────────────────────┐
│ RESERVA INTERMEDIA (ID: 124) - MODIFICADA          │
│ Habitación: 102                                     │
│ Check-in:  12/11 14:00                              │
│ Check-out: 13/11 11:00  ← Automático (antes era 15/11) │
│ Estado:    checkin                                  │
│ connected_booking_id: 125  ← Actualizado           │
│ split_from_booking_id: 123                          │
└─────────────────────────────────────────────────────┘
                        │
                        │
┌─────────────────────────────────────────────────────┐
│ RESERVA ACTUAL (ID: 125) - CREADA                  │
│ Habitación: 103                                     │
│ Check-in:  13/11 15:30  ← Hora diferente           │
│ Check-out: 16/11 12:00  ← Extiende estancia        │
│ Estado:    checkin                                  │
│ Noches:    3 noches                                 │
│ connected_booking_id: 124                           │
│ split_from_booking_id: 124                          │
│ is_room_change_destination: true                    │
└─────────────────────────────────────────────────────┘
```

---

## 🔍 Cómo Obtener Todas las Reservas Conectadas

### **Función para Obtener la Cadena Completa:**

```javascript
// Función recursiva para obtener todas las reservas conectadas
const getConnectedBookingsChain = async (bookingId, visited = new Set(), chain = []) => {
  // Evitar loops infinitos
  if (visited.has(bookingId)) {
    return chain;
  }
  visited.add(bookingId);

  try {
    // Obtener reserva actual
    const response = await fetch(
      `https://tu-servidor.com/api/hotel/reservas/${bookingId}`,
      {
        headers: {
          'X-API-Key': 'tu-api-key'
        }
      }
    );

    const data = await response.json();
    
    if (!response.ok || !data.success) {
      return chain;
    }

    const booking = data.data;
    
    // Agregar a la cadena
    chain.push({
      id: booking.id,
      sequence_id: booking.sequence_id,
      check_in: booking.check_in,
      check_out: booking.check_out,
      status_bar: booking.status_bar,
      rooms: booking.rooms,
      is_origin: booking.is_room_change_origin,
      is_destination: booking.is_room_change_destination,
      connected_to: booking.connected_booking_id,
      split_from: booking.split_from_booking_id
    });

    // Buscar hacia adelante (reserva conectada)
    if (booking.connected_booking_id && !visited.has(booking.connected_booking_id)) {
      await getConnectedBookingsChain(
        booking.connected_booking_id,
        visited,
        chain
      );
    }

    // Buscar hacia atrás (reserva de origen)
    if (booking.split_from_booking_id && !visited.has(booking.split_from_booking_id)) {
      // Insertar al inicio de la cadena
      await getConnectedBookingsChain(
        booking.split_from_booking_id,
        visited,
        chain
      );
    }

    return chain;
  } catch (error) {
    console.error(`Error obteniendo reserva ${bookingId}:`, error);
    return chain;
  }
};

// Uso: Obtener todas las reservas desde cualquier punto de la cadena
const todasLasReservas = await getConnectedBookingsChain(125);
console.log('Cadena completa:', todasLasReservas);

// Ordenar por fecha de check-in
const ordenadas = todasLasReservas.sort((a, b) => {
  return new Date(a.check_in) - new Date(b.check_in);
});

console.log('Reservas ordenadas:', ordenadas);
```

### **Resultado:**

```javascript
[
  {
    id: 123,
    sequence_id: "RES-2024-001",
    check_in: "2024-11-10 14:00:00",
    check_out: "2024-11-12 11:00:00",
    status_bar: "checkin",
    rooms: [{ id: 456, product_id: 10, name: "Habitación 101" }],
    is_origin: true,
    is_destination: false,
    connected_to: 124,
    split_from: null
  },
  {
    id: 124,
    sequence_id: "RES-2024-002",
    check_in: "2024-11-12 14:00:00",
    check_out: "2024-11-13 11:00:00",
    status_bar: "checkin",
    rooms: [{ id: 789, product_id: 11, name: "Habitación 102" }],
    is_origin: false,
    is_destination: false,
    connected_to: 125,
    split_from: 123
  },
  {
    id: 125,
    sequence_id: "RES-2024-003",
    check_in: "2024-11-13 15:30:00",
    check_out: "2024-11-16 12:00:00",
    status_bar: "checkin",
    rooms: [{ id: 890, product_id: 12, name: "Habitación 103" }],
    is_origin: false,
    is_destination: true,
    connected_to: 124,
    split_from: 124
  }
]
```

---

## 📊 Componente React Completo: Historial de Cambios

```jsx
import React, { useState, useEffect } from 'react';

const BookingChangeHistory = ({ bookingId }) => {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadHistory = async () => {
      setLoading(true);
      try {
        const chain = await getConnectedBookingsChain(bookingId);
        const sorted = chain.sort((a, b) => {
          return new Date(a.check_in) - new Date(b.check_in);
        });
        setBookings(sorted);
      } catch (error) {
        console.error('Error:', error);
      } finally {
        setLoading(false);
      }
    };

    if (bookingId) {
      loadHistory();
    }
  }, [bookingId]);

  if (loading) {
    return <div>Cargando historial...</div>;
  }

  return (
    <div className="booking-change-history">
      <h3>Historial de Cambios de Habitación</h3>
      <div className="timeline">
        {bookings.map((booking, index) => (
          <div key={booking.id} className="timeline-item">
            <div className="booking-card">
              <div className="booking-header">
                <span className="sequence">{booking.sequence_id}</span>
                <span className={`badge ${booking.status_bar}`}>
                  {booking.status_bar}
                </span>
                {booking.is_origin && (
                  <span className="label-origin">Origen</span>
                )}
                {booking.is_destination && (
                  <span className="label-destination">Actual</span>
                )}
              </div>
              
              <div className="booking-dates">
                <div>
                  <strong>Check-in:</strong> {new Date(booking.check_in).toLocaleString('es-ES')}
                </div>
                <div>
                  <strong>Check-out:</strong> {new Date(booking.check_out).toLocaleString('es-ES')}
                </div>
              </div>

              <div className="booking-rooms">
                {booking.rooms.map(room => (
                  <span key={room.id} className="room-badge">
                    🏨 {room.name}
                  </span>
                ))}
              </div>

              {index < bookings.length - 1 && (
                <div className="connection-arrow">
                  ↓ Cambio de habitación
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Resumen */}
      <div className="summary">
        <h4>Resumen</h4>
        <p>
          <strong>Total de cambios:</strong> {bookings.length - 1}
        </p>
        <p>
          <strong>Duración total:</strong> {
            Math.ceil(
              (new Date(bookings[bookings.length - 1]?.check_out) - 
               new Date(bookings[0]?.check_in)) / 
              (1000 * 60 * 60 * 24)
            )
          } noches
        </p>
        <p>
          <strong>Habitaciones ocupadas:</strong> {
            bookings.map(b => b.rooms[0]?.name).join(' → ')
          }
        </p>
      </div>
    </div>
  );
};

export default BookingChangeHistory;
```

---

## ✅ Validaciones Completas en Cada Cambio

### **Validaciones que el Backend Ejecuta:**

1. **Validación de Reserva:**
   - ✅ Reserva existe
   - ✅ Reserva no cancelada
   - ✅ Permisos de acceso

2. **Validación de Línea:**
   - ✅ Línea pertenece a la reserva
   - ✅ Si múltiples líneas, `booking_line_id` requerido

3. **Validación de Habitación:**
   - ✅ Nueva habitación diferente a la actual
   - ✅ Nueva habitación existe
   - ✅ Nueva habitación del mismo hotel

4. **Validación de Fechas:**
   - ✅ `change_start_date < change_end_date`
   - ✅ `change_start_date` dentro del período actual
   - ✅ Fechas válidas (formato correcto)

5. **Validación de Disponibilidad:**
   - ✅ Habitación no ocupada en el período
   - ✅ Excluye reservas canceladas
   - ✅ Excluye la reserva actual

6. **Validación de Horas:**
   - ✅ `check_in_hour`: 0-23
   - ✅ `check_in_minute`: 0-59
   - ✅ `check_out_hour`: 0-23
   - ✅ `check_out_minute`: 0-59

7. **Validación de Precio:**
   - ✅ Si `use_custom_price = true`, `custom_price` requerido

---

## 🎯 Resumen del Flujo Completo

```
PASO 1: Reserva Original
├─ ID: 123
├─ Habitación: 101
├─ 10/11 14:00 → 15/11 11:00
└─ 5 noches

PASO 2: Primer Cambio (desde 123)
├─ Reserva 123 modificada: 10/11 → 12/11 (2 noches)
├─ Reserva 124 creada: 12/11 → 15/11 (3 noches)
├─ Habitación: 102
└─ Conectadas: 123 ↔ 124

PASO 3: Segundo Cambio (desde 124)
├─ Reserva 124 modificada: 12/11 → 13/11 (1 noche)
├─ Reserva 125 creada: 13/11 → 16/11 (3 noches)
├─ Habitación: 103
├─ Extiende estancia: +1 día
└─ Conectadas: 124 ↔ 125

CADENA FINAL:
123 → 124 → 125
(101) → (102) → (103)
```

---

## 🚀 Código Helper Completo

```javascript
// helper.js - Funciones reutilizables

export const changeRoom = async (bookingId, changeData) => {
  const payload = {
    booking_line_id: changeData.lineId,
    new_room_id: changeData.newRoomId,
    change_start_date: changeData.startDate,
    change_end_date: changeData.endDate
  };

  // Agregar horas si se proporcionan
  if (changeData.startHour !== null && changeData.startHour !== undefined) {
    payload.check_in_hour = parseInt(changeData.startHour);
    payload.check_in_minute = changeData.startMinute !== null 
      ? parseInt(changeData.startMinute) 
      : 0;
  }

  if (changeData.endHour !== null && changeData.endHour !== undefined) {
    payload.check_out_hour = parseInt(changeData.endHour);
    payload.check_out_minute = changeData.endMinute !== null 
      ? parseInt(changeData.endMinute) 
      : 0;
  }

  // Precio personalizado
  if (changeData.useCustomPrice) {
    payload.use_custom_price = true;
    payload.custom_price = changeData.customPrice;
  }

  // Nota
  if (changeData.note) {
    payload.note = changeData.note;
  }

  const response = await fetch(
    `${API_BASE_URL}/api/hotel/reserva/${bookingId}/change_room`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY
      },
      body: JSON.stringify(payload)
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Error al aplicar cambio');
  }

  return await response.json();
};

export const getBooking = async (bookingId) => {
  const response = await fetch(
    `${API_BASE_URL}/api/hotel/reservas/${bookingId}`,
    {
      headers: {
        'X-API-Key': API_KEY
      }
    }
  );

  if (!response.ok) {
    throw new Error('Error al obtener reserva');
  }

  const data = await response.json();
  return data.data;
};

export const getConnectedChain = async (bookingId) => {
  const visited = new Set();
  const chain = [];

  const traverse = async (id) => {
    if (visited.has(id)) return;
    visited.add(id);

    const booking = await getBooking(id);
    chain.push(booking);

    if (booking.connected_booking_id) {
      await traverse(booking.connected_booking_id);
    }

    if (booking.split_from_booking_id) {
      await traverse(booking.split_from_booking_id);
    }
  };

  await traverse(bookingId);
  
  return chain.sort((a, b) => {
    return new Date(a.check_in) - new Date(b.check_in);
  });
};
```

---

¡Este ejemplo muestra el flujo completo con múltiples cambios, validaciones y manejo de horas! 🎉

