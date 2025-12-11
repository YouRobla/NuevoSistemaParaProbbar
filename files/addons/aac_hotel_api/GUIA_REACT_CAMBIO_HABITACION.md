# 🚀 Guía Completa: Cambio de Habitación desde React

## 📋 Índice
1. [Dos Casos Principales](#dos-casos-principales)
2. [Caso 1: Extender/Modificar Reserva (Misma Habitación)](#caso-1-extendermodificar-reserva)
3. [Caso 2: Cambio de Habitación](#caso-2-cambio-de-habitación)
4. [Cómo Identificar Reservas Conectadas](#cómo-identificar-reservas-conectadas)
5. [Validaciones Paso a Paso](#validaciones-paso-a-paso)
6. [Ejemplos Completos en React](#ejemplos-completos-en-react)

---

## Dos Casos Principales

### **Caso 1: Extender/Modificar Reserva Existente (Misma Habitación)**
**Endpoint:** `PUT /api/hotel/reserva/<reserva_id>`

Permite:
- ✅ Extender fechas de check-out
- ✅ Modificar fechas de check-in/check-out
- ✅ Cambiar horas
- ✅ Actualizar otros campos (descripción, descuentos, etc.)

**NO crea una nueva reserva** - Solo modifica la existente.

---

### **Caso 2: Cambio de Habitación**
**Endpoints:**
- `GET/POST /api/hotel/reserva/<booking_id>/change_room/options` - Obtener opciones
- `POST /api/hotel/reserva/<booking_id>/change_room` - Aplicar cambio

Permite:
- ✅ Cambiar a otra habitación
- ✅ Modificar fechas del cambio
- ✅ Extender período más allá de la reserva original
- ✅ Usar precio personalizado

**SÍ crea una nueva reserva** conectada a la original.

---

## Caso 1: Extender/Modificar Reserva

### **Endpoint**
```
PUT /api/hotel/reserva/<reserva_id>
```

### **Headers Requeridos**
```javascript
{
  'Content-Type': 'application/json',
  'X-API-Key': 'tu-api-key'  // o 'Authorization': 'Bearer tu-api-key'
}
```

### **Payload - Datos a Enviar**

```typescript
interface UpdateBookingPayload {
  // Fechas (opcionales)
  check_in?: string;           // "2024-01-15" o "2024-01-15 14:00:00"
  check_out?: string;          // "2024-01-20" o "2024-01-20 11:00:00"
  
  // Estado (opcional)
  status_bar?: string;         // 'confirmed', 'checkin', 'checkout', etc.
  
  // Otros campos (opcionales)
  partner_id?: number;
  hotel_id?: number;
  user_id?: number;
  description?: string;
  motivo_viaje?: string;
  booking_discount?: number;
  discount_reason?: string;
  
  // Cargos adicionales (opcionales)
  early_checkin_charge?: number;
  late_checkout_charge?: number;
  manual_service_description?: string;
  manual_service_amount?: number;
  
  // Datos de agente (opcional)
  via_agent?: boolean;
  agent_id?: number;
  commission_type?: 'fixed' | 'percentage';
  agent_commission_amount?: number;
  agent_commission_percentage?: number;
}
```

### **Ejemplo: Extender Check-Out**

```javascript
// Función para extender check-out
const extendCheckout = async (reservaId, newCheckoutDate, newCheckoutTime = null) => {
  const payload = {
    check_out: newCheckoutTime 
      ? `${newCheckoutDate} ${newCheckoutTime}`  // "2024-01-25 11:00:00"
      : newCheckoutDate                          // "2024-01-25"
  };

  try {
    const response = await fetch(
      `https://tu-servidor.com/api/hotel/reserva/${reservaId}`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'tu-api-key'
        },
        body: JSON.stringify(payload)
      }
    );

    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || 'Error al actualizar reserva');
    }

    return data;
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
};

// Uso
const result = await extendCheckout(123, '2024-01-25', '11:00:00');
console.log('Reserva actualizada:', result.data);
```

### **Respuesta del API**

```typescript
interface UpdateBookingResponse {
  success: boolean;
  message: string;
  data: {
    id: number;
    sequence_id: string;
    partner_id: number;
    check_in: string;              // "2024-01-10 14:00:00"
    check_out: string;             // "2024-01-25 11:00:00"
    check_in_hour: number | null;  // 14
    check_in_minute: number | null; // 0
    check_out_hour: number | null;  // 11
    check_out_minute: number | null; // 0
    status_bar: string;
    hotel_id: number;
    // ... otros campos
  }
}
```

### **Validaciones del Endpoint**

1. ✅ **Reserva existe** - Verifica que la reserva con ID existe
2. ✅ **Permisos** - Verifica acceso de lectura/escritura
3. ✅ **Fechas válidas** - `check_in < check_out`
4. ✅ **Transición de estado** - Valida que el cambio de estado sea permitido
5. ✅ **Partner válido** - Si se proporciona `partner_id`, debe existir
6. ✅ **Hotel válido** - Si se proporciona `hotel_id`, debe existir

---

## Caso 2: Cambio de Habitación

### **Flujo Completo: 2 Pasos**

#### **Paso 1: Obtener Opciones de Cambio**

**Endpoint:**
```
GET/POST /api/hotel/reserva/<booking_id>/change_room/options
```

**Headers:**
```javascript
{
  'Content-Type': 'application/json',
  'X-API-Key': 'tu-api-key'
}
```

**Payload (Opcional):**
```json
{
  "booking_line_id": 456  // Solo necesario si la reserva tiene múltiples líneas
}
```

**Respuesta:**
```typescript
interface ChangeRoomOptionsResponse {
  success: boolean;
  data: {
    defaults: {
      booking_id: number;
      booking_line_id: number;
      booking_line_name: string;
      current_room_id: number;
      current_room_name: string;
      current_room_code: string;
      current_room_capacity: {
        max_adult: number | null;
        max_child: number | null;
      };
      current_room_price: number;
      current_room_discount: number;
      current_room_subtotal: number;
      current_room_total: number;
      current_room_currency: {
        id: number | null;
        name: string | null;
        symbol: string | null;
      };
      change_start_date: string;      // "2024-01-15" (propuesto)
      change_end_date: string;        // "2024-01-20" (propuesto)
      total_nights: number;           // 5
      estimated_total: number;        // 500.00
      use_custom_price: boolean;
      custom_price: number | false;
    };
    available_rooms: Array<{
      id: number;
      name: string;
      code: string;
      price: number;
    }>;
  }
}
```

**Ejemplo en React:**
```javascript
// Función para obtener opciones de cambio
const getChangeRoomOptions = async (bookingId, lineId = null) => {
  const payload = lineId ? { booking_line_id: lineId } : {};

  try {
    const response = await fetch(
      `https://tu-servidor.com/api/hotel/reserva/${bookingId}/change_room/options`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'tu-api-key'
        },
        body: JSON.stringify(payload)
      }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Error al obtener opciones');
    }

    return data;
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
};

// Uso
const options = await getChangeRoomOptions(123, 456);
console.log('Habitaciones disponibles:', options.data.available_rooms);
console.log('Fechas propuestas:', options.data.defaults.change_start_date, '→', options.data.defaults.change_end_date);
```

---

#### **Paso 2: Aplicar el Cambio de Habitación**

**Endpoint:**
```
POST /api/hotel/reserva/<booking_id>/change_room
```

**Headers:**
```javascript
{
  'Content-Type': 'application/json',
  'X-API-Key': 'tu-api-key'
}
```

**Payload - Datos a Enviar:**

```typescript
interface ChangeRoomPayload {
  // REQUERIDO
  booking_line_id: number;       // ID de la línea de reserva a cambiar
  new_room_id: number;           // ID de la nueva habitación
  
  // Fechas - 3 FORMAS de enviarlas (elige una):
  
  // FORMA 1: Horas separadas (RECOMENDADO)
  change_start_date: string;     // "2024-01-15"
  change_end_date: string;       // "2024-01-20"
  check_in_hour?: number;        // 14 (0-23)
  check_in_minute?: number;      // 0 (0-59)
  check_out_hour?: number;       // 11 (0-23)
  check_out_minute?: number;     // 0 (0-59)
  
  // FORMA 2: DateTime completo
  // change_start_datetime?: string;  // "2024-01-15 14:00:00"
  // change_end_datetime?: string;    // "2024-01-20 11:00:00"
  
  // FORMA 3: Solo fechas (usará horas de la reserva original)
  // change_start_date: string;     // "2024-01-15"
  // change_end_date: string;       // "2024-01-20"
  
  // OPCIONAL
  use_custom_price?: boolean;    // false
  custom_price?: number;         // Solo si use_custom_price = true
  note?: string;                 // Nota sobre el cambio
}
```

**Ejemplo Completo en React:**
```javascript
// Función para aplicar cambio de habitación
const applyRoomChange = async (bookingId, changeData) => {
  const {
    lineId,
    newRoomId,
    startDate,
    endDate,
    startHour = null,
    startMinute = null,
    endHour = null,
    endMinute = null,
    useCustomPrice = false,
    customPrice = null,
    note = ''
  } = changeData;

  // Construir payload
  const payload = {
    booking_line_id: lineId,
    new_room_id: newRoomId,
    change_start_date: startDate,
    change_end_date: endDate,
    use_custom_price: useCustomPrice,
    note: note
  };

  // Agregar horas si se proporcionaron
  if (startHour !== null) {
    payload.check_in_hour = startHour;
    payload.check_in_minute = startMinute !== null ? startMinute : 0;
  }

  if (endHour !== null) {
    payload.check_out_hour = endHour;
    payload.check_out_minute = endMinute !== null ? endMinute : 0;
  }

  // Agregar precio personalizado si se usa
  if (useCustomPrice && customPrice !== null) {
    payload.custom_price = customPrice;
  }

  try {
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

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Error al aplicar cambio de habitación');
    }

    return data;
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
};

// Uso - Ejemplo 1: Cambio básico con horas
const result1 = await applyRoomChange(123, {
  lineId: 456,
  newRoomId: 11,
  startDate: '2024-01-15',
  endDate: '2024-01-20',
  startHour: 14,
  startMinute: 0,
  endHour: 11,
  endMinute: 0,
  note: 'Cambio solicitado por el cliente'
});

// Uso - Ejemplo 2: Cambio con precio personalizado
const result2 = await applyRoomChange(123, {
  lineId: 456,
  newRoomId: 11,
  startDate: '2024-01-15',
  endDate: '2024-01-20',
  useCustomPrice: true,
  customPrice: 90.00,
  note: 'Cambio con descuento especial'
});

// Uso - Ejemplo 3: Cambio sin horas (usará las originales)
const result3 = await applyRoomChange(123, {
  lineId: 456,
  newRoomId: 11,
  startDate: '2024-01-15',
  endDate: '2024-01-20'
});
```

**Respuesta del API:**
```typescript
interface ChangeRoomResponse {
  success: boolean;
  message: string;
  data: {
    reserva_id: number;           // ID de la reserva original
    action: any;                   // Acción de Odoo (puede ignorarse)
    new_reserva?: {                // NUEVA RESERVA CREADA
      id: number;                  // ID de la nueva reserva
      sequence_id: string;         // "RES-2024-001"
      check_in: string;            // "2024-01-15 14:00:00"
      check_out: string;           // "2024-01-20 11:00:00"
      check_in_hour: number | null;
      check_in_minute: number | null;
      check_out_hour: number | null;
      check_out_minute: number | null;
      status_bar: string;          // "checkin"
    };
  }
}
```

---

## Cómo Identificar Reservas Conectadas

### **Campos que Indican Conexión**

Cuando obtienes una reserva con `GET /api/hotel/reservas/<id>`, verifica estos campos:

```typescript
interface BookingWithConnection {
  id: number;
  sequence_id: string;
  // ... otros campos ...
  
  // CAMPOS DE CONEXIÓN
  split_from_booking_id?: number | null;        // ID de reserva de origen
  connected_booking_id?: number | null;         // ID de reserva conectada
  is_room_change_origin?: boolean;              // true si es la reserva original
  is_room_change_destination?: boolean;         // true si es la nueva reserva
  
  // Objeto completo de la reserva conectada (si existe)
  connected_booking?: {
    id: number;
    sequence_id: string;
    check_in: string;
    check_out: string;
    status_bar: string;
    rooms: Array<{
      id: number;
      name: string;
      product_id: number;
    }>;
    // ... otros campos ...
  } | null;
}
```

### **Lógica de Conexión**

```
┌─────────────────────────────────────┐
│ RESERVA ORIGINAL (ID: 123)          │
│                                     │
│ split_from_booking_id: null         │
│ connected_booking_id: 124  ←───────┼───┐
│ is_room_change_origin: true         │   │
│ is_room_change_destination: false   │   │
└─────────────────────────────────────┘   │
                                          │
                                          │ Conexión bidireccional
                                          │
┌─────────────────────────────────────┐   │
│ NUEVA RESERVA (ID: 124)             │   │
│                                     │   │
│ split_from_booking_id: 123  ←───────┼───┘
│ connected_booking_id: 123           │
│ is_room_change_origin: false        │
│ is_room_change_destination: true    │
└─────────────────────────────────────┘
```

### **Función para Obtener Todas las Reservas Conectadas**

```javascript
// Función recursiva para obtener todas las reservas conectadas
const getConnectedBookings = async (bookingId, visited = new Set(), allBookings = []) => {
  // Evitar loops infinitos
  if (visited.has(bookingId)) {
    return allBookings;
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
      return allBookings;
    }

    const booking = data.data;
    allBookings.push(booking);

    // Si tiene reserva conectada, obtenerla también
    if (booking.connected_booking_id && !visited.has(booking.connected_booking_id)) {
      await getConnectedBookings(
        booking.connected_booking_id, 
        visited, 
        allBookings
      );
    }

    // Si es una reserva que se dividió, obtener la original
    if (booking.split_from_booking_id && !visited.has(booking.split_from_booking_id)) {
      await getConnectedBookings(
        booking.split_from_booking_id,
        visited,
        allBookings
      );
    }

    return allBookings;
  } catch (error) {
    console.error(`Error obteniendo reserva ${bookingId}:`, error);
    return allBookings;
  }
};

// Uso
const allConnected = await getConnectedBookings(123);
console.log('Todas las reservas conectadas:', allConnected);

// Ordenar por fecha de check-in
const sorted = allConnected.sort((a, b) => {
  return new Date(a.check_in) - new Date(b.check_in);
});

console.log('Reservas ordenadas:', sorted);
```

### **Componente React para Mostrar Reservas Conectadas**

```jsx
import React, { useState, useEffect } from 'react';

const ConnectedBookingsList = ({ bookingId }) => {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadConnectedBookings = async () => {
      setLoading(true);
      try {
        const allBookings = await getConnectedBookings(bookingId);
        
        // Ordenar por fecha
        const sorted = allBookings.sort((a, b) => {
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
      loadConnectedBookings();
    }
  }, [bookingId]);

  if (loading) {
    return <div>Cargando reservas conectadas...</div>;
  }

  return (
    <div className="connected-bookings">
      <h3>Reservas Conectadas ({bookings.length})</h3>
      {bookings.map((booking, index) => (
        <div key={booking.id} className="booking-card">
          <div className="booking-header">
            <span className="booking-id">{booking.sequence_id}</span>
            <span className={`badge ${booking.status_bar}`}>
              {booking.status_bar}
            </span>
          </div>
          <div className="booking-dates">
            <span>Check-in: {new Date(booking.check_in).toLocaleDateString()}</span>
            <span>Check-out: {new Date(booking.check_out).toLocaleDateString()}</span>
          </div>
          <div className="booking-rooms">
            {booking.rooms?.map(room => (
              <span key={room.id} className="room-tag">
                {room.name}
              </span>
            ))}
          </div>
          {booking.is_room_change_origin && (
            <span className="connection-badge">Origen</span>
          )}
          {booking.is_room_change_destination && (
            <span className="connection-badge">Destino</span>
          )}
          {index < bookings.length - 1 && (
            <div className="connection-line">↓</div>
          )}
        </div>
      ))}
    </div>
  );
};

export default ConnectedBookingsList;
```

---

## Validaciones Paso a Paso

### **Validaciones del Endpoint de Cambio de Habitación**

#### **1. Validación de Reserva**
```javascript
// ✅ La reserva debe existir
if (!booking.exists()) {
  throw new Error('La reserva solicitada no existe.');
}
```

#### **2. Validación de Línea de Reserva**
```javascript
// ✅ La línea debe pertenecer a la reserva
if (line_id && !line.exists()) {
  throw new Error('La línea de reserva indicada no pertenece a la reserva.');
}

// ✅ Si hay múltiples líneas, debe especificarse line_id
if (!line_id && booking.booking_line_ids.length > 1) {
  throw new Error('Debe especificar booking_line_id cuando la reserva tiene múltiples líneas.');
}
```

#### **3. Validación de Nueva Habitación**
```javascript
// ✅ Debe proporcionar new_room_id
if (!new_room_id) {
  throw new Error('Debe proporcionar new_room_id.');
}

// ✅ La nueva habitación debe ser diferente
if (new_room_id === current_room_id) {
  throw new Error('Please select a different room.');
}
```

#### **4. Validación de Fechas**
```javascript
// ✅ Debe proporcionar fechas
if (!change_start_date || !change_end_date) {
  throw new Error('Please select both start and end dates for the room change.');
}

// ✅ Fecha inicio < Fecha fin
if (change_start_date >= change_end_date) {
  throw new Error('Change start date must be before change end date.');
}

// ✅ Fecha inicio debe estar dentro del período original
if (!(original_start <= change_start_date < change_end_date)) {
  throw new Error('Change start date must be within the original booking period.');
}

// ✅ Fecha inicio no puede ser antes de la original
if (change_start_date < original_start) {
  throw new Error('Change start date cannot be before the original booking start date.');
}
```

#### **5. Validación de Disponibilidad**
```javascript
// ✅ Verifica que la nueva habitación esté disponible
if (!is_room_available(new_room_id, change_start_date, change_end_date)) {
  throw new Error('The selected room is not available for the chosen period.');
}
```

**Cómo funciona la validación de disponibilidad:**
- Busca otras reservas que usen la misma habitación
- Excluye reservas canceladas (`cancelled`, `no_show`)
- Verifica solapamiento de fechas:
  - `other_booking.check_in < change_end_date`
  - `other_booking.check_out > change_start_date`
- Si encuentra solapamiento → Habitación NO disponible

#### **6. Validación de Precio Personalizado**
```javascript
// ✅ Si use_custom_price = true, debe proporcionar custom_price
if (use_custom_price && custom_price === false) {
  throw new Error('Please enter a custom price. You can enter 0 if you want the room change to be free.');
}
```

#### **7. Validación de Horas (si se proporcionan)**
```javascript
// ✅ Horas deben ser válidas
if (check_in_hour !== null) {
  if (check_in_hour < 0 || check_in_hour > 23) {
    throw new Error('check_in_hour must be between 0 and 23.');
  }
  if (check_in_minute < 0 || check_in_minute > 59) {
    throw new Error('check_in_minute must be between 0 and 59.');
  }
}
```

---

## Ejemplos Completos en React

### **Componente Completo: Modal de Cambio de Habitación**

```jsx
import React, { useState, useEffect } from 'react';

const RoomChangeModal = ({ bookingId, lineId, onClose, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [options, setOptions] = useState(null);
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
  const [errors, setErrors] = useState({});

  // Cargar opciones al abrir el modal
  useEffect(() => {
    const loadOptions = async () => {
      try {
        const response = await getChangeRoomOptions(bookingId, lineId);
        setOptions(response.data);
        
        // Prellenar formulario con valores por defecto
        const defaults = response.data.defaults;
        setFormData(prev => ({
          ...prev,
          startDate: defaults.change_start_date,
          endDate: defaults.change_end_date,
          // Usar horas de la reserva actual si están disponibles
          startHour: defaults.change_start_date.includes(' ') 
            ? parseInt(defaults.change_start_date.split(' ')[1].split(':')[0])
            : null,
          endHour: defaults.change_end_date.includes(' ')
            ? parseInt(defaults.change_end_date.split(' ')[1].split(':')[0])
            : null
        }));
      } catch (error) {
        console.error('Error cargando opciones:', error);
        alert('Error al cargar opciones de cambio');
      }
    };

    if (bookingId) {
      loadOptions();
    }
  }, [bookingId, lineId]);

  // Validar formulario
  const validateForm = () => {
    const newErrors = {};

    if (!formData.newRoomId) {
      newErrors.newRoomId = 'Debe seleccionar una habitación';
    }

    if (!formData.startDate) {
      newErrors.startDate = 'Debe especificar fecha de inicio';
    }

    if (!formData.endDate) {
      newErrors.endDate = 'Debe especificar fecha de fin';
    }

    if (formData.startDate && formData.endDate) {
      if (new Date(formData.startDate) >= new Date(formData.endDate)) {
        newErrors.endDate = 'La fecha de fin debe ser posterior a la de inicio';
      }
    }

    if (formData.useCustomPrice && !formData.customPrice) {
      newErrors.customPrice = 'Debe especificar un precio personalizado';
    }

    if (formData.startHour !== null && (formData.startHour < 0 || formData.startHour > 23)) {
      newErrors.startHour = 'Hora debe estar entre 0 y 23';
    }

    if (formData.startMinute !== null && (formData.startMinute < 0 || formData.startMinute > 59)) {
      newErrors.startMinute = 'Minuto debe estar entre 0 y 59';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Manejar envío
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setLoading(true);
    try {
      const result = await applyRoomChange(bookingId, {
        lineId: lineId,
        newRoomId: parseInt(formData.newRoomId),
        startDate: formData.startDate,
        endDate: formData.endDate,
        startHour: formData.startHour,
        startMinute: formData.startMinute,
        endHour: formData.endHour,
        endMinute: formData.endMinute,
        useCustomPrice: formData.useCustomPrice,
        customPrice: formData.useCustomPrice ? parseFloat(formData.customPrice) : null,
        note: formData.note
      });

      if (result.success) {
        alert('Cambio de habitación aplicado exitosamente');
        if (onSuccess) {
          onSuccess(result.data);
        }
        onClose();
      }
    } catch (error) {
      console.error('Error:', error);
      alert(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (!options) {
    return <div>Cargando opciones...</div>;
  }

  const { defaults, available_rooms } = options;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>Cambiar Habitación</h2>
        
        <div className="current-room-info">
          <h3>Habitación Actual</h3>
          <p><strong>{defaults.current_room_name}</strong> ({defaults.current_room_code})</p>
          <p>Precio actual: {defaults.current_room_currency.symbol} {defaults.current_room_total}</p>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Selección de nueva habitación */}
          <div className="form-group">
            <label>
              Nueva Habitación <span className="required">*</span>
            </label>
            <select
              value={formData.newRoomId}
              onChange={(e) => setFormData({ ...formData, newRoomId: e.target.value })}
              className={errors.newRoomId ? 'error' : ''}
            >
              <option value="">Seleccionar...</option>
              {available_rooms.map(room => (
                <option key={room.id} value={room.id}>
                  {room.name} ({room.code}) - {defaults.current_room_currency.symbol} {room.price}/noche
                </option>
              ))}
            </select>
            {errors.newRoomId && <span className="error-message">{errors.newRoomId}</span>}
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
                className={errors.startDate ? 'error' : ''}
              />
              {errors.startDate && <span className="error-message">{errors.startDate}</span>}
            </div>

            <div className="form-group">
              <label>
                Fecha Fin <span className="required">*</span>
              </label>
              <input
                type="date"
                value={formData.endDate}
                onChange={(e) => setFormData({ ...formData, endDate: e.target.value })}
                className={errors.endDate ? 'error' : ''}
              />
              {errors.endDate && <span className="error-message">{errors.endDate}</span>}
            </div>
          </div>

          {/* Horas (opcionales) */}
          <div className="form-row">
            <div className="form-group">
              <label>Hora Check-in (opcional)</label>
              <div className="time-inputs">
                <input
                  type="number"
                  min="0"
                  max="23"
                  placeholder="14"
                  value={formData.startHour ?? ''}
                  onChange={(e) => setFormData({ ...formData, startHour: e.target.value ? parseInt(e.target.value) : null })}
                  className={errors.startHour ? 'error' : ''}
                />
                <span>:</span>
                <input
                  type="number"
                  min="0"
                  max="59"
                  placeholder="0"
                  value={formData.startMinute ?? ''}
                  onChange={(e) => setFormData({ ...formData, startMinute: e.target.value ? parseInt(e.target.value) : null })}
                  className={errors.startMinute ? 'error' : ''}
                />
              </div>
            </div>

            <div className="form-group">
              <label>Hora Check-out (opcional)</label>
              <div className="time-inputs">
                <input
                  type="number"
                  min="0"
                  max="23"
                  placeholder="11"
                  value={formData.endHour ?? ''}
                  onChange={(e) => setFormData({ ...formData, endHour: e.target.value ? parseInt(e.target.value) : null })}
                />
                <span>:</span>
                <input
                  type="number"
                  min="0"
                  max="59"
                  placeholder="0"
                  value={formData.endMinute ?? ''}
                  onChange={(e) => setFormData({ ...formData, endMinute: e.target.value ? parseInt(e.target.value) : null })}
                />
              </div>
            </div>
          </div>

          {/* Precio personalizado */}
          <div className="form-group">
            <label>
              <input
                type="checkbox"
                checked={formData.useCustomPrice}
                onChange={(e) => setFormData({ ...formData, useCustomPrice: e.target.checked })}
              />
              Usar precio personalizado
            </label>
            {formData.useCustomPrice && (
              <input
                type="number"
                step="0.01"
                placeholder="90.00"
                value={formData.customPrice}
                onChange={(e) => setFormData({ ...formData, customPrice: e.target.value })}
                className={errors.customPrice ? 'error' : ''}
              />
            )}
            {errors.customPrice && <span className="error-message">{errors.customPrice}</span>}
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

          {/* Información de estimación */}
          {formData.newRoomId && formData.startDate && formData.endDate && (
            <div className="estimation-info">
              <p><strong>Noches estimadas:</strong> {
                Math.max(0, Math.ceil((new Date(formData.endDate) - new Date(formData.startDate)) / (1000 * 60 * 60 * 24)))
              }</p>
              {!formData.useCustomPrice && available_rooms.find(r => r.id === parseInt(formData.newRoomId)) && (
                <p><strong>Total estimado:</strong> {
                  defaults.current_room_currency.symbol
                } {
                  available_rooms.find(r => r.id === parseInt(formData.newRoomId)).price * 
                  Math.max(0, Math.ceil((new Date(formData.endDate) - new Date(formData.startDate)) / (1000 * 60 * 60 * 24)))
                }</p>
              )}
            </div>
          )}

          {/* Botones */}
          <div className="form-actions">
            <button type="button" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button type="submit" disabled={loading}>
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

### **Hook Personalizado para Cambio de Habitación**

```javascript
import { useState, useCallback } from 'react';

const useRoomChange = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const getOptions = useCallback(async (bookingId, lineId = null) => {
    setLoading(true);
    setError(null);
    try {
      const result = await getChangeRoomOptions(bookingId, lineId);
      return result;
    } catch (err) {
      setError(err.message);
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
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    getOptions,
    applyChange,
    loading,
    error
  };
};

export default useRoomChange;
```

### **Uso del Hook**

```jsx
import useRoomChange from './hooks/useRoomChange';

const MyComponent = () => {
  const { getOptions, applyChange, loading, error } = useRoomChange();

  const handleChangeRoom = async () => {
    try {
      // Paso 1: Obtener opciones
      const options = await getOptions(123, 456);
      console.log('Opciones:', options);

      // Paso 2: Aplicar cambio
      const result = await applyChange(123, {
        lineId: 456,
        newRoomId: 11,
        startDate: '2024-01-15',
        endDate: '2024-01-20',
        startHour: 14,
        startMinute: 0
      });

      console.log('Cambio aplicado:', result);
    } catch (err) {
      console.error('Error:', err);
    }
  };

  return (
    <div>
      {loading && <div>Cargando...</div>}
      {error && <div className="error">{error}</div>}
      <button onClick={handleChangeRoom}>Cambiar Habitación</button>
    </div>
  );
};
```

---

## Resumen de Endpoints

| Caso | Método | Endpoint | Descripción |
|------|--------|----------|-------------|
| **Extender/Modificar** | PUT | `/api/hotel/reserva/<id>` | Modifica reserva existente |
| **Obtener Opciones** | GET/POST | `/api/hotel/reserva/<id>/change_room/options` | Obtiene habitaciones disponibles |
| **Aplicar Cambio** | POST | `/api/hotel/reserva/<id>/change_room` | Crea nueva reserva conectada |
| **Ver Reserva** | GET | `/api/hotel/reservas/<id>` | Obtiene reserva con datos de conexión |

---

## Checklist de Implementación

- [ ] Configurar API Key en variables de entorno
- [ ] Crear funciones helper para llamadas API
- [ ] Implementar validación de formularios
- [ ] Manejar errores y mensajes de validación
- [ ] Mostrar opciones de habitaciones disponibles
- [ ] Permitir selección de fechas y horas
- [ ] Implementar opción de precio personalizado
- [ ] Mostrar estimación de precio antes de confirmar
- [ ] Actualizar UI después de cambio exitoso
- [ ] Implementar visualización de reservas conectadas
- [ ] Manejar estados de carga y errores

---

¡Listo! Esta guía cubre todo lo necesario para implementar el cambio de habitación desde React. 🎉

