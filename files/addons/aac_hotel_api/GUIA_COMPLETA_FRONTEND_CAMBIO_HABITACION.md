# 🚀 Guía Completa Frontend: Cambio de Habitación

## 📋 Índice

1. [Resumen de Endpoints](#resumen-de-endpoints)
2. [Configuración Inicial](#configuración-inicial)
3. [Caso 1: Cambio Básico (Sin Horas)](#caso-1-cambio-básico-sin-horas)
4. [Caso 2: Cambio con Horas Exactas](#caso-2-cambio-con-horas-exactas)
5. [Caso 3: Cambio con Precio Personalizado](#caso-3-cambio-con-precio-personalizado)
6. [Caso 4: Cambio Durante la Reserva](#caso-4-cambio-durante-la-reserva)
7. [Caso 5: Cambio Después de la Reserva (Gap)](#caso-5-cambio-después-de-la-reserva-gap)
8. [Caso 6: Múltiples Cambios en Secuencia](#caso-6-múltiples-cambios-en-secuencia)
9. [Manejo de Respuestas](#manejo-de-respuestas)
10. [Manejo de Errores](#manejo-de-errores)
11. [Obtener Reservas Conectadas](#obtener-reservas-conectadas)

---

## 🔗 Resumen de Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET/POST` | `/api/hotel/reserva/<booking_id>/change_room/options` | Obtener opciones de cambio |
| `POST` | `/api/hotel/reserva/<booking_id>/change_room` | Aplicar cambio de habitación |
| `GET` | `/api/hotel/reservas/<booking_id>` | Obtener reserva con datos de conexión |

---

## ⚙️ Configuración Inicial

### **Variables de Entorno**

```javascript
// config.js
export const API_CONFIG = {
  BASE_URL: 'https://tu-servidor.com',
  API_KEY: 'tu-api-key-aqui'
};
```

### **Función Helper para Llamadas API**

```javascript
// api/helpers.js
import { API_CONFIG } from '../config';

export const apiRequest = async (endpoint, method = 'GET', data = null) => {
  const url = `${API_CONFIG.BASE_URL}${endpoint}`;
  
  const options = {
    method,
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_CONFIG.API_KEY
      // O también puedes usar: 'Authorization': `Bearer ${API_CONFIG.API_KEY}`
    }
  };

  if (data && (method === 'POST' || method === 'PUT')) {
    options.body = JSON.stringify(data);
  }

  try {
    const response = await fetch(url, options);
    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || `Error ${response.status}: ${response.statusText}`);
    }

    return result;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
};
```

---

## 📦 Caso 1: Cambio Básico (Sin Horas)

### **Escenario:**
- Reserva original: 10/11 → 15/11 (Habitación 101)
- Cambio: El 12/11 a Habitación 102 hasta el 15/11

### **Paso 1: Obtener Opciones (OPCIONAL - Solo para mostrar al usuario)**

> **⚠️ IMPORTANTE:** Este paso es **OPCIONAL**. Solo lo necesitas si quieres mostrar habitaciones disponibles y precios al usuario antes de aplicar el cambio.
>
> **El backend hace TODO automáticamente en el Paso 2.** No necesitas hacer múltiples llamadas para actualizar.

```javascript
// api/roomChange.js
export const getChangeRoomOptions = async (bookingId, lineId = null) => {
  const payload = lineId ? { booking_line_id: lineId } : {};
  
  const response = await apiRequest(
    `/api/hotel/reserva/${bookingId}/change_room/options`,
    'POST',
    payload
  );
  
  return response;
};

// Uso (OPCIONAL - Solo si quieres mostrar opciones al usuario)
const options = await getChangeRoomOptions(123, 456);
console.log('Opciones:', options.data);
// Muestra: habitaciones disponibles, precios, fechas sugeridas
```

**Respuesta del API:**

```json
{
  "success": true,
  "data": {
    "defaults": {
      "booking_id": 123,
      "booking_line_id": 456,
      "current_room_id": 10,
      "current_room_name": "Habitación 101",
      "current_room_code": "RM101",
      "current_room_price": 100.00,
      "change_start_date": "2024-11-12",
      "change_end_date": "2024-11-15",
      "total_nights": 3,
      "estimated_total": 300.00
    },
    "available_rooms": [
      {
        "id": 11,
        "name": "Habitación 102",
        "code": "RM102",
        "price": 120.00
      },
      {
        "id": 12,
        "name": "Habitación 103",
        "code": "RM103",
        "price": 150.00
      }
    ]
  }
}
```

### **Paso 2: Aplicar Cambio (ESTE HACE TODO - ÚNICA LLAMADA NECESARIA)**

> **✅ IMPORTANTE:** Esta es la **ÚNICA llamada necesaria** para aplicar el cambio. El backend hace TODO automáticamente:
> - ✅ Modifica la reserva original
> - ✅ Crea la nueva reserva
> - ✅ Conecta ambas reservas
> - ✅ Transfiere servicios y facturación
>
> **No necesitas hacer otra llamada para "actualizar".**

```javascript
// api/roomChange.js
export const applyRoomChange = async (bookingId, changeData) => {
  const payload = {
    booking_line_id: changeData.lineId,
    new_room_id: changeData.newRoomId,
    change_start_date: changeData.startDate,
    change_end_date: changeData.endDate
    // NO se envían horas - el backend usará las horas originales
  };

  // Agregar precio personalizado si se usa
  if (changeData.useCustomPrice) {
    payload.use_custom_price = true;
    payload.custom_price = changeData.customPrice;
  }

  // Agregar nota si se proporciona
  if (changeData.note) {
    payload.note = changeData.note;
  }

  // ✅ ESTA LLAMADA HACE TODO:
  // - Modifica reserva original
  // - Crea nueva reserva
  // - Conecta ambas
  // - Transfiere servicios y facturación
  const response = await apiRequest(
    `/api/hotel/reserva/${bookingId}/change_room`,
    'POST',
    payload
  );

  return response;
};

// Uso
const result = await applyRoomChange(123, {
  lineId: 456,
  newRoomId: 11,
  startDate: '2024-11-12',
  endDate: '2024-11-15'
});

console.log('Cambio aplicado:', result);
```

**Payload Enviado:**

```json
{
  "booking_line_id": 456,
  "new_room_id": 11,
  "change_start_date": "2024-11-12",
  "change_end_date": "2024-11-15"
}
```

**Respuesta del API:**

```json
{
  "success": true,
  "message": "Cambio de habitación aplicado correctamente.",
  "data": {
    "reserva_id": 123,
    "new_reserva": {
      "id": 124,
      "sequence_id": "RES-2024-002",
      "check_in": "2024-11-12 14:00:00",
      "check_out": "2024-11-15 11:00:00",
      "check_in_hour": 14,
      "check_in_minute": 0,
      "check_out_hour": 11,
      "check_out_minute": 0,
      "status_bar": "checkin"
    }
  }
}
```

**Resultado (TODO hecho por el backend en esta llamada):**
- ✅ Reserva original: 10/11 14:00 → 12/11 11:00 (YA MODIFICADA en el backend)
- ✅ Nueva reserva: 12/11 14:00 → 15/11 11:00 (YA CREADA en el backend)
- ✅ Ambas reservas YA ESTÁN CONECTADAS en la base de datos

**No necesitas hacer otra llamada para actualizar. Todo está listo.**

---

## ⏰ Caso 2: Cambio con Horas Exactas

### **Escenario:**
- Reserva original: 10/11 14:00 → 15/11 11:00
- Cambio: El 12/11 a las 15:30 a Habitación 102

### **Código Frontend:**

```javascript
const result = await applyRoomChange(123, {
  lineId: 456,
  newRoomId: 11,
  startDate: '2024-11-12',
  endDate: '2024-11-15',
  startHour: 15,        // Hora exacta para check-in
  startMinute: 30,
  endHour: 12,          // Hora exacta para check-out
  endMinute: 0
});
```

### **Función Actualizada:**

```javascript
// api/roomChange.js
export const applyRoomChange = async (bookingId, changeData) => {
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

  return await apiRequest(
    `/api/hotel/reserva/${bookingId}/change_room`,
    'POST',
    payload
  );
};
```

**Payload Enviado:**

```json
{
  "booking_line_id": 456,
  "new_room_id": 11,
  "change_start_date": "2024-11-12",
  "change_end_date": "2024-11-15",
  "check_in_hour": 15,
  "check_in_minute": 30,
  "check_out_hour": 12,
  "check_out_minute": 0
}
```

**Respuesta del API:**

```json
{
  "success": true,
  "data": {
    "new_reserva": {
      "id": 124,
      "check_in": "2024-11-12 15:30:00",
      "check_out": "2024-11-15 12:00:00",
      "check_in_hour": 15,
      "check_in_minute": 30,
      "check_out_hour": 12,
      "check_out_minute": 0
    }
  }
}
```

**Resultado:**
- Reserva original: 10/11 14:00 → 12/11 11:00 (si check-out original 11:00 <= cambio 15:30, mantiene 11:00)
- Nueva reserva: 12/11 15:30 → 15/11 12:00 (usa horas especificadas)

---

## 💰 Caso 3: Cambio con Precio Personalizado

### **Escenario:**
- Cambio con descuento especial
- Precio personalizado: $90/noche en lugar de $120

### **Código Frontend:**

```javascript
const result = await applyRoomChange(123, {
  lineId: 456,
  newRoomId: 11,
  startDate: '2024-11-12',
  endDate: '2024-11-15',
  useCustomPrice: true,
  customPrice: 90.00,
  note: 'Cambio con descuento especial del 25%'
});
```

**Payload Enviado:**

```json
{
  "booking_line_id": 456,
  "new_room_id": 11,
  "change_start_date": "2024-11-12",
  "change_end_date": "2024-11-15",
  "use_custom_price": true,
  "custom_price": 90.00,
  "note": "Cambio con descuento especial del 25%"
}
```

**Resultado:**
- Nueva reserva usa precio de $90/noche en lugar del precio de lista

---

## 📅 Caso 4: Cambio Durante la Reserva

### **Escenario:**
- Reserva original: 10/11 → 15/11 (Habitación 101)
- Cambio: El 12/11 a Habitación 102 hasta el 18/11 (extiende)

### **Código Frontend:**

```javascript
const result = await applyRoomChange(123, {
  lineId: 456,
  newRoomId: 11,
  startDate: '2024-11-12',  // Durante la reserva original
  endDate: '2024-11-18',    // Extiende 3 días más
  startHour: 14,
  startMinute: 0
});
```

**Payload Enviado:**

```json
{
  "booking_line_id": 456,
  "new_room_id": 11,
  "change_start_date": "2024-11-12",
  "change_end_date": "2024-11-18",
  "check_in_hour": 14,
  "check_in_minute": 0
}
```

**Respuesta del API:**

```json
{
  "success": true,
  "data": {
    "reserva_id": 123,
    "new_reserva": {
      "id": 124,
      "check_in": "2024-11-12 14:00:00",
      "check_out": "2024-11-18 11:00:00",
      "status_bar": "checkin"
    }
  }
}
```

**Resultado:**
- Reserva original: 10/11 14:00 → 12/11 11:00 (acortada)
- Nueva reserva: 12/11 14:00 → 18/11 11:00 (extiende 3 días más)

---

## 🕐 Caso 5: Cambio Después de la Reserva (Gap)

### **Escenario:**
- Reserva original: 10/11 → 13/11 (Habitación 101)
- Cambio: El 15/11 a Habitación 102 hasta el 18/11
- Gap: 2 días (13/11 - 15/11)

### **Código Frontend:**

```javascript
const result = await applyRoomChange(123, {
  lineId: 456,
  newRoomId: 11,
  startDate: '2024-11-15',  // DESPUÉS del check-out original (13/11)
  endDate: '2024-11-18',
  startHour: 14,
  startMinute: 0
});
```

**Payload Enviado:**

```json
{
  "booking_line_id": 456,
  "new_room_id": 11,
  "change_start_date": "2024-11-15",
  "change_end_date": "2024-11-18",
  "check_in_hour": 14,
  "check_in_minute": 0
}
```

**Respuesta del API:**

```json
{
  "success": true,
  "data": {
    "reserva_id": 123,
    "new_reserva": {
      "id": 124,
      "check_in": "2024-11-15 14:00:00",
      "check_out": "2024-11-18 11:00:00",
      "status_bar": "checkin",
      "connected_booking_id": 123
    }
  }
}
```

**Resultado:**
- Reserva original: 10/11 14:00 → 13/11 11:00 (**NO SE MODIFICA**)
- Gap: 13/11 - 15/11 (2 días sin reserva)
- Nueva reserva: 15/11 14:00 → 18/11 11:00
- Ambas reservas están **conectadas** para seguimiento

---

## 🔄 Caso 6: Múltiples Cambios en Secuencia

### **Escenario:**
1. Reserva original: 10/11 → 15/11 (Habitación 101)
2. Primer cambio: 12/11 → Habitación 102 hasta 15/11
3. Segundo cambio: 13/11 → Habitación 103 hasta 18/11

### **Paso 1: Primer Cambio**

```javascript
// Desde la reserva original (ID: 123)
const primerCambio = await applyRoomChange(123, {
  lineId: 456,              // Línea de la reserva 123
  newRoomId: 11,            // Habitación 102
  startDate: '2024-11-12',
  endDate: '2024-11-15',
  startHour: 14,
  startMinute: 0
});

console.log('Primer cambio:', primerCambio.data.new_reserva);
// Nueva reserva creada: ID 124
```

### **Paso 2: Obtener Datos de la Nueva Reserva**

```javascript
// api/booking.js
export const getBooking = async (bookingId) => {
  const response = await apiRequest(`/api/hotel/reservas/${bookingId}`, 'GET');
  return response.data;
};

// Obtener datos de la reserva 124
const reserva124 = await getBooking(124);
console.log('Reserva 124:', reserva124);
```

### **Paso 3: Segundo Cambio (desde reserva 124)**

```javascript
// Ahora trabajar con la reserva 124 (la creada en el primer cambio)
const segundoCambio = await applyRoomChange(124, {
  lineId: reserva124.rooms[0].id,  // ID de la línea de la reserva 124
  newRoomId: 12,                    // Habitación 103
  startDate: '2024-11-13',
  endDate: '2024-11-18',            // Extiende estancia
  startHour: 15,
  startMinute: 30,
  note: 'Segundo cambio y extensión'
});

console.log('Segundo cambio:', segundoCambio.data.new_reserva);
// Nueva reserva creada: ID 125
```

**Cadena Completa:**
```
Reserva 123 (Original): 10/11 → 12/11 (Habitación 101)
    ↓
Reserva 124 (Primer cambio): 12/11 → 13/11 (Habitación 102)
    ↓
Reserva 125 (Segundo cambio): 13/11 → 18/11 (Habitación 103)
```

---

## 📥 Manejo de Respuestas

### **Estructura de Respuesta Estándar**

```typescript
interface ChangeRoomResponse {
  success: boolean;
  message: string;
  data: {
    reserva_id: number;           // ID de la reserva original
    action?: any;                  // Acción de Odoo (puede ignorarse)
    new_reserva?: {                // Nueva reserva creada
      id: number;
      sequence_id: string;
      check_in: string;            // "2024-11-12 14:00:00"
      check_out: string;           // "2024-11-15 11:00:00"
      check_in_hour: number | null;
      check_in_minute: number | null;
      check_out_hour: number | null;
      check_out_minute: number | null;
      status_bar: string;
      connected_booking_id?: number;
    };
  }
}
```

### **Función para Procesar Respuesta**

```javascript
// utils/roomChangeResponse.js
export const processChangeRoomResponse = (response) => {
  if (!response.success) {
    throw new Error(response.error || 'Error al aplicar cambio');
  }

  const { reserva_id, new_reserva } = response.data;

  return {
    originalBookingId: reserva_id,
    newBooking: new_reserva ? {
      id: new_reserva.id,
      sequenceId: new_reserva.sequence_id,
      checkIn: new_reserva.check_in,
      checkOut: new_reserva.check_out,
      checkInTime: new_reserva.check_in_hour !== null 
        ? `${String(new_reserva.check_in_hour).padStart(2, '0')}:${String(new_reserva.check_in_minute || 0).padStart(2, '0')}`
        : null,
      checkOutTime: new_reserva.check_out_hour !== null
        ? `${String(new_reserva.check_out_hour).padStart(2, '0')}:${String(new_reserva.check_out_minute || 0).padStart(2, '0')}`
        : null,
      status: new_reserva.status_bar,
      connectedTo: new_reserva.connected_booking_id
    } : null
  };
};

// Uso
const result = await applyRoomChange(123, changeData);
const processed = processChangeRoomResponse(result);

console.log('Reserva original:', processed.originalBookingId);
console.log('Nueva reserva:', processed.newBooking);
```

---

## ❌ Manejo de Errores

### **Tipos de Errores Comunes**

#### **1. Error de Validación**

```javascript
try {
  const result = await applyRoomChange(123, {
    lineId: 456,
    newRoomId: 11,
    startDate: '2024-11-15',
    endDate: '2024-11-12'  // ❌ Fecha fin antes de inicio
  });
} catch (error) {
  if (error.message.includes('Change start date must be before change end date')) {
    // Manejar error de fechas
    alert('La fecha de fin debe ser posterior a la de inicio');
  }
}
```

#### **2. Habitación No Disponible**

```javascript
try {
  const result = await applyRoomChange(123, changeData);
} catch (error) {
  if (error.message.includes('not available')) {
    // Habitación ocupada en ese período
    alert('La habitación seleccionada no está disponible en las fechas elegidas');
    // Mostrar opciones de fechas disponibles
  }
}
```

#### **3. Error de Horas (Mismo Día)**

```javascript
try {
  const result = await applyRoomChange(123, {
    lineId: 456,
    newRoomId: 11,
    startDate: '2024-11-13',  // Mismo día que check-out original
    endDate: '2024-11-18',
    startHour: 10,             // ❌ Menor que check-out original (11:00)
    startMinute: 0
  });
} catch (error) {
  if (error.message.includes('no puede ser después de la hora del cambio')) {
    // El check-out original es mayor que la hora del cambio
    alert('El check-out de la reserva original no puede ser después de la hora del cambio. Por favor ajuste la hora.');
  }
}
```

### **Función Helper para Manejo de Errores**

```javascript
// utils/errorHandler.js
export const handleRoomChangeError = (error) => {
  const errorMessage = error.message || error.toString();

  // Mapeo de errores a mensajes amigables
  const errorMessages = {
    'Change start date must be before change end date': 
      'La fecha de fin debe ser posterior a la fecha de inicio',
    'not available': 
      'La habitación no está disponible en las fechas seleccionadas. Por favor elija otras fechas.',
    'no puede ser después de la hora del cambio': 
      'El check-out de la reserva original no puede ser después de la hora del cambio. Ajuste la hora del cambio.',
    'Please select a different room': 
      'Debe seleccionar una habitación diferente a la actual',
    'Booking must have a valid check-in and check-out date': 
      'La reserva no tiene fechas válidas',
    'Please select both start and end dates': 
      'Debe seleccionar ambas fechas para el cambio'
  };

  // Buscar mensaje personalizado
  for (const [key, message] of Object.entries(errorMessages)) {
    if (errorMessage.includes(key)) {
      return message;
    }
  }

  // Mensaje por defecto
  return errorMessage || 'Ocurrió un error al aplicar el cambio de habitación';
};

// Uso
try {
  const result = await applyRoomChange(123, changeData);
  // Éxito
} catch (error) {
  const friendlyMessage = handleRoomChangeError(error);
  alert(friendlyMessage);
  console.error('Error detallado:', error);
}
```

---

## 🔗 Obtener Reservas Conectadas

### **Función para Obtener Cadena Completa**

```javascript
// api/booking.js
export const getConnectedBookings = async (bookingId, visited = new Set(), chain = []) => {
  // Evitar loops infinitos
  if (visited.has(bookingId)) {
    return chain;
  }
  visited.add(bookingId);

  try {
    // Obtener reserva actual
    const booking = await getBooking(bookingId);
    
    // Agregar a la cadena
    chain.push({
      id: booking.id,
      sequenceId: booking.sequence_id,
      checkIn: booking.check_in,
      checkOut: booking.check_out,
      status: booking.status_bar,
      rooms: booking.rooms || [],
      isOrigin: booking.is_room_change_origin || false,
      isDestination: booking.is_room_change_destination || false,
      connectedTo: booking.connected_booking_id,
      splitFrom: booking.split_from_booking_id
    });

    // Buscar hacia adelante (reserva conectada)
    if (booking.connected_booking_id && !visited.has(booking.connected_booking_id)) {
      await getConnectedBookings(
        booking.connected_booking_id,
        visited,
        chain
      );
    }

    // Buscar hacia atrás (reserva de origen)
    if (booking.split_from_booking_id && !visited.has(booking.split_from_booking_id)) {
      await getConnectedBookings(
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

// Uso
const allConnected = await getConnectedBookings(125);
console.log('Cadena completa:', allConnected);

// Ordenar por fecha de check-in
const sorted = allConnected.sort((a, b) => {
  return new Date(a.checkIn) - new Date(b.checkIn);
});

console.log('Reservas ordenadas:', sorted);
```

### **Respuesta de getBooking**

```json
{
  "id": 124,
  "sequence_id": "RES-2024-002",
  "check_in": "2024-11-12 14:00:00",
  "check_out": "2024-11-15 11:00:00",
  "status_bar": "checkin",
  "rooms": [
    {
      "id": 789,
      "product_id": 11,
      "name": "Habitación 102"
    }
  ],
  "connected_booking_id": 123,
  "split_from_booking_id": 123,
  "is_room_change_origin": false,
  "is_room_change_destination": true
}
```

---

## 📝 Componente React Completo

### **Hook Personalizado**

```javascript
// hooks/useRoomChange.js
import { useState, useCallback } from 'react';
import { getChangeRoomOptions, applyRoomChange } from '../api/roomChange';
import { handleRoomChangeError } from '../utils/errorHandler';

export const useRoomChange = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [options, setOptions] = useState(null);

  const loadOptions = useCallback(async (bookingId, lineId = null) => {
    setLoading(true);
    setError(null);
    try {
      const result = await getChangeRoomOptions(bookingId, lineId);
      setOptions(result.data);
      return result.data;
    } catch (err) {
      const friendlyError = handleRoomChangeError(err);
      setError(friendlyError);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const applyChange = useCallback(async (bookingId, changeData) => {
    setLoading(true);
    setError(null);
    try {
      const result = await applyRoomChange(bookingId, changeData);
      return result;
    } catch (err) {
      const friendlyError = handleRoomChangeError(err);
      setError(friendlyError);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loadOptions,
    applyChange,
    options,
    loading,
    error,
    clearError: () => setError(null)
  };
};
```

### **Componente de Modal**

```jsx
// components/RoomChangeModal.jsx
import React, { useState, useEffect } from 'react';
import { useRoomChange } from '../hooks/useRoomChange';

const RoomChangeModal = ({ bookingId, lineId, onClose, onSuccess }) => {
  const { loadOptions, applyChange, options, loading, error } = useRoomChange();
  
  const [formData, setFormData] = useState({
    newRoomId: '',
    startDate: '',
    endDate: '',
    startHour: null,
    startMinute: null,
    endHour: null,
    endMinute: null,
    useCustomPrice: false,
    customPrice: '',
    note: ''
  });

  const [useCustomTime, setUseCustomTime] = useState(false);

  // Cargar opciones al abrir
  useEffect(() => {
    if (bookingId) {
      loadOptions(bookingId, lineId);
    }
  }, [bookingId, lineId, loadOptions]);

  // Prellenar formulario cuando se cargan las opciones
  useEffect(() => {
    if (options?.defaults) {
      const defaults = options.defaults;
      setFormData(prev => ({
        ...prev,
        startDate: defaults.change_start_date || '',
        endDate: defaults.change_end_date || ''
      }));
    }
  }, [options]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const changeData = {
        lineId: lineId || options?.defaults?.booking_line_id,
        newRoomId: parseInt(formData.newRoomId),
        startDate: formData.startDate,
        endDate: formData.endDate
      };

      // Agregar horas si se usan
      if (useCustomTime) {
        if (formData.startHour !== null) {
          changeData.startHour = parseInt(formData.startHour);
          changeData.startMinute = formData.startMinute !== null 
            ? parseInt(formData.startMinute) 
            : 0;
        }
        if (formData.endHour !== null) {
          changeData.endHour = parseInt(formData.endHour);
          changeData.endMinute = formData.endMinute !== null 
            ? parseInt(formData.endMinute) 
            : 0;
        }
      }

      // Precio personalizado
      if (formData.useCustomPrice) {
        changeData.useCustomPrice = true;
        changeData.customPrice = parseFloat(formData.customPrice);
      }

      // Nota
      if (formData.note) {
        changeData.note = formData.note;
      }

      const result = await applyChange(bookingId, changeData);

      if (result.success) {
        if (onSuccess) {
          onSuccess(result.data);
        }
        onClose();
      }
    } catch (err) {
      // Error ya manejado en el hook
      console.error('Error al aplicar cambio:', err);
    }
  };

  if (loading && !options) {
    return <div className="modal">Cargando opciones...</div>;
  }

  const { defaults, available_rooms } = options || {};

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>Cambiar Habitación</h2>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {defaults && (
          <div className="current-room-info">
            <h3>Habitación Actual</h3>
            <p><strong>{defaults.current_room_name}</strong> ({defaults.current_room_code})</p>
            <p>Precio actual: {defaults.current_room_currency?.symbol} {defaults.current_room_total}</p>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Selección de nueva habitación */}
          <div className="form-group">
            <label>
              Nueva Habitación <span className="required">*</span>
            </label>
            <select
              value={formData.newRoomId}
              onChange={(e) => setFormData({ ...formData, newRoomId: e.target.value })}
              required
            >
              <option value="">Seleccionar...</option>
              {available_rooms?.map(room => (
                <option key={room.id} value={room.id}>
                  {room.name} ({room.code}) - {defaults?.current_room_currency?.symbol} {room.price}/noche
                </option>
              ))}
            </select>
          </div>

          {/* Fechas */}
          <div className="form-row">
            <div className="form-group">
              <label>
                Fecha Inicio <span className="required">*</span>
              </label>
              <input
                type="date"
                value={formData.startDate}
                onChange={(e) => setFormData({ ...formData, startDate: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label>
                Fecha Fin <span className="required">*</span>
              </label>
              <input
                type="date"
                value={formData.endDate}
                onChange={(e) => setFormData({ ...formData, endDate: e.target.value })}
                required
              />
            </div>
          </div>

          {/* Horas personalizadas */}
          <div className="form-group">
            <label>
              <input
                type="checkbox"
                checked={useCustomTime}
                onChange={(e) => setUseCustomTime(e.target.checked)}
              />
              Especificar horas exactas
            </label>
          </div>

          {useCustomTime && (
            <div className="form-row">
              <div className="form-group">
                <label>Hora Check-in</label>
                <div className="time-inputs">
                  <input
                    type="number"
                    min="0"
                    max="23"
                    placeholder="14"
                    value={formData.startHour ?? ''}
                    onChange={(e) => setFormData({ 
                      ...formData, 
                      startHour: e.target.value ? parseInt(e.target.value) : null 
                    })}
                  />
                  <span>:</span>
                  <input
                    type="number"
                    min="0"
                    max="59"
                    placeholder="0"
                    value={formData.startMinute ?? ''}
                    onChange={(e) => setFormData({ 
                      ...formData, 
                      startMinute: e.target.value ? parseInt(e.target.value) : null 
                    })}
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Hora Check-out</label>
                <div className="time-inputs">
                  <input
                    type="number"
                    min="0"
                    max="23"
                    placeholder="11"
                    value={formData.endHour ?? ''}
                    onChange={(e) => setFormData({ 
                      ...formData, 
                      endHour: e.target.value ? parseInt(e.target.value) : null 
                    })}
                  />
                  <span>:</span>
                  <input
                    type="number"
                    min="0"
                    max="59"
                    placeholder="0"
                    value={formData.endMinute ?? ''}
                    onChange={(e) => setFormData({ 
                      ...formData, 
                      endMinute: e.target.value ? parseInt(e.target.value) : null 
                    })}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Precio personalizado */}
          <div className="form-group">
            <label>
              <input
                type="checkbox"
                checked={formData.useCustomPrice}
                onChange={(e) => setFormData({ 
                  ...formData, 
                  useCustomPrice: e.target.checked 
                })}
              />
              Usar precio personalizado
            </label>
            {formData.useCustomPrice && (
              <input
                type="number"
                step="0.01"
                placeholder="90.00"
                value={formData.customPrice}
                onChange={(e) => setFormData({ 
                  ...formData, 
                  customPrice: e.target.value 
                })}
              />
            )}
          </div>

          {/* Nota */}
          <div className="form-group">
            <label>Nota (opcional)</label>
            <textarea
              value={formData.note}
              onChange={(e) => setFormData({ ...formData, note: e.target.value })}
              rows="3"
            />
          </div>

          {/* Información estimada */}
          {formData.newRoomId && formData.startDate && formData.endDate && available_rooms && (
            <div className="estimation-info">
              {(() => {
                const selectedRoom = available_rooms.find(r => r.id === parseInt(formData.newRoomId));
                const start = new Date(formData.startDate);
                const end = new Date(formData.endDate);
                const nights = Math.max(0, Math.ceil((end - start) / (1000 * 60 * 60 * 24)));
                const price = formData.useCustomPrice 
                  ? parseFloat(formData.customPrice) 
                  : (selectedRoom?.price || 0);
                
                return (
                  <>
                    <p><strong>Noches estimadas:</strong> {nights}</p>
                    <p><strong>Total estimado:</strong> {defaults?.current_room_currency?.symbol} {price * nights}</p>
                  </>
                );
              })()}
            </div>
          )}

          {/* Botones */}
          <div className="form-actions">
            <button type="button" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button type="submit" disabled={loading || !formData.newRoomId}>
              {loading ? 'Procesando...' : 'Aplicar Cambio'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default RoomChangeModal;
```

### **Componente para Mostrar Historial**

```jsx
// components/BookingChangeHistory.jsx
import React, { useState, useEffect } from 'react';
import { getConnectedBookings } from '../api/booking';

const BookingChangeHistory = ({ bookingId }) => {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadHistory = async () => {
      setLoading(true);
      try {
        const chain = await getConnectedBookings(bookingId);
        const sorted = chain.sort((a, b) => {
          return new Date(a.checkIn) - new Date(b.checkIn);
        });
        setBookings(sorted);
      } catch (error) {
        console.error('Error cargando historial:', error);
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
                <span className="sequence">{booking.sequenceId}</span>
                <span className={`badge ${booking.status}`}>
                  {booking.status}
                </span>
                {booking.isOrigin && (
                  <span className="label-origin">Origen</span>
                )}
                {booking.isDestination && (
                  <span className="label-destination">Actual</span>
                )}
              </div>
              
              <div className="booking-dates">
                <div>
                  <strong>Check-in:</strong> {new Date(booking.checkIn).toLocaleString('es-ES')}
                </div>
                <div>
                  <strong>Check-out:</strong> {new Date(booking.checkOut).toLocaleString('es-ES')}
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

      {bookings.length > 0 && (
        <div className="summary">
          <h4>Resumen</h4>
          <p><strong>Total de cambios:</strong> {bookings.length - 1}</p>
          <p>
            <strong>Duración total:</strong> {
              Math.ceil(
                (new Date(bookings[bookings.length - 1]?.checkOut) - 
                 new Date(bookings[0]?.checkIn)) / 
                (1000 * 60 * 60 * 24)
              )
            } noches
          </p>
          <p>
            <strong>Habitaciones ocupadas:</strong> {
              bookings.map(b => b.rooms[0]?.name).filter(Boolean).join(' → ')
            }
          </p>
        </div>
      )}
    </div>
  );
};

export default BookingChangeHistory;
```

---

## 📊 Resumen de Payloads por Caso

### **Caso 1: Cambio Básico**
```json
{
  "booking_line_id": 456,
  "new_room_id": 11,
  "change_start_date": "2024-11-12",
  "change_end_date": "2024-11-15"
}
```

### **Caso 2: Con Horas**
```json
{
  "booking_line_id": 456,
  "new_room_id": 11,
  "change_start_date": "2024-11-12",
  "change_end_date": "2024-11-15",
  "check_in_hour": 14,
  "check_in_minute": 0,
  "check_out_hour": 11,
  "check_out_minute": 0
}
```

### **Caso 3: Con Precio Personalizado**
```json
{
  "booking_line_id": 456,
  "new_room_id": 11,
  "change_start_date": "2024-11-12",
  "change_end_date": "2024-11-15",
  "use_custom_price": true,
  "custom_price": 90.00
}
```

### **Caso 4: Cambio Durante (Extiende)**
```json
{
  "booking_line_id": 456,
  "new_room_id": 11,
  "change_start_date": "2024-11-12",
  "change_end_date": "2024-11-18"
}
```

### **Caso 5: Cambio Después (Gap)**
```json
{
  "booking_line_id": 456,
  "new_room_id": 11,
  "change_start_date": "2024-11-15",
  "change_end_date": "2024-11-18"
}
```

### **Caso 6: Completo**
```json
{
  "booking_line_id": 456,
  "new_room_id": 11,
  "change_start_date": "2024-11-12",
  "change_end_date": "2024-11-18",
  "check_in_hour": 14,
  "check_in_minute": 0,
  "check_out_hour": 11,
  "check_out_minute": 0,
  "use_custom_price": true,
  "custom_price": 90.00,
  "note": "Cambio con descuento especial"
}
```

---

## ✅ Checklist de Implementación

- [ ] Configurar API Key en variables de entorno
- [ ] Crear funciones helper para llamadas API
- [ ] Implementar `getChangeRoomOptions()`
- [ ] Implementar `applyRoomChange()`
- [ ] Implementar validación de formularios
- [ ] Manejar errores con mensajes amigables
- [ ] Mostrar opciones de habitaciones disponibles
- [ ] Permitir selección de fechas y horas
- [ ] Implementar opción de precio personalizado
- [ ] Mostrar estimación de precio antes de confirmar
- [ ] Actualizar UI después de cambio exitoso
- [ ] Implementar visualización de reservas conectadas
- [ ] Manejar estados de carga y errores

---

## 🎯 Ejemplos de Uso Completo

### **Ejemplo 1: Flujo Completo Simple**

```javascript
// 1. Obtener opciones
const options = await getChangeRoomOptions(123, 456);
console.log('Habitaciones disponibles:', options.data.available_rooms);

// 2. Aplicar cambio
const result = await applyRoomChange(123, {
  lineId: 456,
  newRoomId: options.data.available_rooms[0].id,
  startDate: options.data.defaults.change_start_date,
  endDate: options.data.defaults.change_end_date
});

// 3. Mostrar resultado
if (result.success) {
  alert(`Cambio aplicado. Nueva reserva: ${result.data.new_reserva.sequence_id}`);
  
  // 4. Recargar datos de la reserva
  const updatedBooking = await getBooking(123);
  console.log('Reserva actualizada:', updatedBooking);
}
```

### **Ejemplo 2: Con Validaciones y Manejo de Errores**

```javascript
const handleRoomChange = async (bookingId, lineId, changeData) => {
  try {
    // Validar fechas antes de enviar
    const start = new Date(changeData.startDate);
    const end = new Date(changeData.endDate);
    
    if (start >= end) {
      throw new Error('La fecha de fin debe ser posterior a la de inicio');
    }

    // Aplicar cambio
    const result = await applyRoomChange(bookingId, {
      lineId,
      ...changeData
    });

    return {
      success: true,
      data: result.data
    };
  } catch (error) {
    const friendlyMessage = handleRoomChangeError(error);
    return {
      success: false,
      error: friendlyMessage
    };
  }
};

// Uso
const result = await handleRoomChange(123, 456, {
  newRoomId: 11,
  startDate: '2024-11-12',
  endDate: '2024-11-15',
  startHour: 14,
  startMinute: 0
});

if (result.success) {
  console.log('Cambio exitoso:', result.data);
} else {
  alert(result.error);
}
```

---

**¡Documento completo para implementar el cambio de habitación desde el frontend!** 🎉

