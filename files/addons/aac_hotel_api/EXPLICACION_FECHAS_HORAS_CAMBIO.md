# ⏰ Explicación: Manejo de Fechas y Horas en Cambio de Habitación

## 📅 Tu Caso Específico

### **Escenario:**
- **Reserva Original:** 10/11 al 12/11 (2 noches)
- **Cambio el día:** 11/11
- **Nueva Habitación:** 11/11 al 14/11 (3 noches)

### **¿Qué pasa automáticamente en el Backend?**

El backend **AUTOMÁTICAMENTE** calcula y actualiza las fechas. **NO necesitas calcularlo en el frontend**.

---

## 🔄 Cómo Funciona el Backend

### **Lógica Automática:**

Cuando envías:
```json
{
  "booking_line_id": 456,
  "new_room_id": 11,
  "change_start_date": "2024-11-11",  // ← Día del cambio
  "change_end_date": "2024-11-14",    // ← Hasta cuándo en la nueva habitación
  "check_in_hour": 14,                // Opcional: hora check-in nueva habitación
  "check_in_minute": 0,
  "check_out_hour": 11,               // Opcional: hora check-out nueva habitación
  "check_out_minute": 0
}
```

**El backend hace automáticamente:**

#### **1. Reserva Original (Modificada):**

```python
# Código del backend (línea 181-206)
original_end_date = change_start_date  # 11/11 (misma fecha del cambio)
original_days = (original_end_date - start).days  # (11/11 - 10/11) = 1 día

# Check-out de la reserva original
new_checkout = fields.Datetime.to_datetime(original_end_date)  # 11/11 00:00:00
# Preserva la HORA ORIGINAL de check-out
new_checkout = new_checkout.replace(
    hour=booking.check_out.hour,      # Hora original (ej: 11:00)
    minute=booking.check_out.minute,  # Minuto original (ej: 00)
    second=booking.check_out.second
)
```

**Resultado:**
- ✅ Check-out original: **11/11 a las 11:00 AM** (hora original preservada)
- ✅ `booking_days` actualizado: **1 noche** (de 10/11 a 11/11)

#### **2. Nueva Reserva (Creada):**

```python
# Código del backend (línea 226-241)
new_checkin = fields.Datetime.to_datetime(change_start_date)  # 11/11 00:00:00
# Usa la HORA PROPORCIONADA o la HORA ORIGINAL de check-in
if hasattr(booking.check_in, 'time'):
    new_checkin = new_checkin.replace(
        hour=check_in_hour or booking.check_in.hour,      # Hora proporcionada o original
        minute=check_in_minute or booking.check_in.minute,
        second=booking.check_in.second
    )

new_checkout = fields.Datetime.to_datetime(change_end_date)  # 14/11 00:00:00
# Usa la HORA PROPORCIONADA o la HORA ORIGINAL de check-out
if hasattr(booking.check_out, 'time'):
    new_checkout = new_checkout.replace(
        hour=check_out_hour or booking.check_out.hour,
        minute=check_out_minute or booking.check_out.minute,
        second=booking.check_out.second
    )
```

**Resultado:**
- ✅ Check-in nueva: **11/11 a las 14:00** (hora proporcionada o original)
- ✅ Check-out nueva: **14/11 a las 11:00** (hora proporcionada o original)

---

## 📊 Resultado Final

```
┌─────────────────────────────────────────────────────────┐
│ RESERVA ORIGINAL (MODIFICADA)                          │
│ Habitación: 101                                         │
│ Check-in:  10/11 14:00                                  │
│ Check-out: 11/11 11:00  ← AUTOMÁTICO (misma fecha del cambio) │
│ Estado:    checkin                                      │
│ Noches:    1 noche                                      │
└─────────────────────────────────────────────────────────┘
                        │
                        │ Cambio de habitación
                        │
┌─────────────────────────────────────────────────────────┐
│ NUEVA RESERVA (CREADA)                                  │
│ Habitación: 102                                         │
│ Check-in:  11/11 14:00  ← Fecha del cambio             │
│ Check-out: 14/11 11:00                                  │
│ Estado:    checkin                                      │
│ Noches:    3 noches                                     │
└─────────────────────────────────────────────────────────┘
```

---

## ⏰ Manejo de Horas

### **Opciones para Manejar Horas:**

#### **Opción 1: No Enviar Horas (Recomendado para este caso)**

```javascript
// El frontend SOLO envía las fechas
const payload = {
  booking_line_id: 456,
  new_room_id: 11,
  change_start_date: "2024-11-11",  // Solo fecha
  change_end_date: "2024-11-14"     // Solo fecha
};

// El backend AUTOMÁTICAMENTE:
// - Reserva original: Check-out 11/11 a la MISMA HORA original (ej: 11:00)
// - Nueva reserva: Check-in 11/11 a la MISMA HORA original de check-in (ej: 14:00)
```

**Ventaja:** Simple, el backend preserva las horas originales automáticamente.

---

#### **Opción 2: Especificar Horas Explícitas**

```javascript
// El frontend especifica horas diferentes
const payload = {
  booking_line_id: 456,
  new_room_id: 11,
  change_start_date: "2024-11-11",
  change_end_date: "2024-11-14",
  // Horas para la NUEVA reserva
  check_in_hour: 15,      // Check-in nueva habitación a las 15:00
  check_in_minute: 0,
  check_out_hour: 12,     // Check-out nueva habitación a las 12:00
  check_out_minute: 0
};

// El backend:
// - Reserva original: Check-out 11/11 a la HORA ORIGINAL (11:00) ← NO cambia
// - Nueva reserva: Check-in 11/11 a las 15:00 (hora especificada)
// - Nueva reserva: Check-out 14/11 a las 12:00 (hora especificada)
```

**Ventaja:** Control total sobre las horas de la nueva reserva.

---

#### **Opción 3: Enviar DateTime Completo**

```javascript
// El frontend envía datetime completo
const payload = {
  booking_line_id: 456,
  new_room_id: 11,
  change_start_datetime: "2024-11-11 15:00:00",  // DateTime completo
  change_end_datetime: "2024-11-14 12:00:00"     // DateTime completo
};

// El backend extrae fecha y hora automáticamente
```

---

## 🎯 Respuesta a tus Preguntas

### **1. ¿El check-out del anterior será automáticamente esa fecha?**

**SÍ, AUTOMÁTICAMENTE**

El backend **SIEMPRE** establece el check-out de la reserva original como la **misma fecha** del `change_start_date`.

**Ejemplo:**
- Si `change_start_date = "2024-11-11"`
- Entonces `check_out original = "2024-11-11"` (automático)

---

### **2. ¿Cómo se manejan las horas?**

**El backend preserva las horas originales por defecto:**

- **Check-out reserva original:** Mantiene la **hora original de check-out**
- **Check-in nueva reserva:** Usa la **hora proporcionada** o la **hora original de check-in**

**Ejemplo:**
- Reserva original check-out original: 12/11 a las **11:00 AM**
- `change_start_date = "2024-11-11"`
- Resultado: Check-out original = 11/11 a las **11:00 AM** (hora preservada)

---

### **3. ¿Lo maneja el backend o el frontend?**

**✅ El BACKEND lo maneja automáticamente**

El frontend **SOLO necesita enviar:**
- `change_start_date`: Fecha de inicio del cambio (11/11)
- `change_end_date`: Fecha de fin en la nueva habitación (14/11)
- `check_in_hour`, `check_in_minute` (opcional): Solo si quieres horas específicas
- `check_out_hour`, `check_out_minute` (opcional): Solo si quieres horas específicas

**El backend:**
- ✅ Calcula automáticamente el check-out de la reserva original
- ✅ Preserva las horas originales (o usa las proporcionadas)
- ✅ Crea la nueva reserva con las fechas correctas
- ✅ Conecta ambas reservas

---

## 📝 Ejemplo Práctico Completo

### **Situación:**
- Reserva original: **10/11/2024 14:00** → **12/11/2024 11:00**
- Cambio el día: **11/11/2024**
- Nueva habitación hasta: **14/11/2024**

### **Código Frontend (React):**

```javascript
// Función para aplicar el cambio
const handleRoomChange = async () => {
  const payload = {
    booking_line_id: 456,
    new_room_id: 11,
    change_start_date: "2024-11-11",  // ← Solo necesitas esta fecha
    change_end_date: "2024-11-14",    // ← Y esta fecha
    
    // Opcional: Si quieres cambiar las horas
    // check_in_hour: 15,
    // check_in_minute: 0,
    // check_out_hour: 12,
    // check_out_minute: 0,
    
    note: "Cambio solicitado para el 11/11"
  };

  try {
    const response = await fetch(
      `https://tu-servidor.com/api/hotel/reserva/123/change_room`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'tu-api-key'
        },
        body: JSON.stringify(payload)
      }
    );

    const result = await response.json();
    
    if (result.success) {
      console.log('✅ Cambio aplicado exitosamente');
      console.log('Reserva original modificada:', {
        check_out: result.data.reserva_id,  // ID de la original
        // El check-out ahora es: 11/11/2024 11:00 (automático)
      });
      console.log('Nueva reserva creada:', result.data.new_reserva);
      // {
      //   id: 124,
      //   check_in: "2024-11-11 14:00:00",
      //   check_out: "2024-11-14 11:00:00"
      // }
    }
  } catch (error) {
    console.error('Error:', error);
  }
};
```

### **Resultado Automático del Backend:**

```javascript
// Lo que recibes del backend:
{
  success: true,
  data: {
    reserva_id: 123,  // Reserva original
    
    // Al consultar esta reserva con GET /api/hotel/reservas/123:
    // {
    //   check_in: "2024-11-10 14:00:00",
    //   check_out: "2024-11-11 11:00:00",  ← AUTOMÁTICO (antes era 12/11)
    //   booking_days: 1,                   ← AUTOMÁTICO (antes era 2)
    //   connected_booking_id: 124          ← AUTOMÁTICO
    // }
    
    new_reserva: {
      id: 124,
      check_in: "2024-11-11 14:00:00",  // Misma hora que check-in original
      check_out: "2024-11-14 11:00:00", // Misma hora que check-out original
      status_bar: "checkin",
      connected_booking_id: 123          ← AUTOMÁTICO
    }
  }
}
```

---

## ⚠️ Puntos Importantes

### **1. Solapamiento en el Mismo Día**

Ambas reservas tienen la **misma fecha (11/11)** pero con **horas diferentes**:
- Reserva original check-out: **11/11 a las 11:00 AM**
- Nueva reserva check-in: **11/11 a las 14:00 PM**

Esto es **CORRECTO** y **PERMITIDO** porque:
- El huésped sale de la habitación 101 a las 11:00 AM
- El huésped entra a la habitación 102 a las 14:00 PM (mismo día)
- Hay un intervalo entre ambas (3 horas)

---

### **2. Si Quieres que el Check-out y Check-in Sean el Mismo Día a la Misma Hora**

Si necesitas que sea exactamente a la misma hora, simplemente **no envíes horas** y el backend usará las horas originales. Si necesitas horas diferentes, especifícalas explícitamente.

---

### **3. Validación de Disponibilidad**

El backend valida que la **nueva habitación esté disponible** desde `change_start_date` hasta `change_end_date`, considerando **solo las fechas** (no las horas específicas para la validación de solapamiento).

---

## 🎯 Resumen

| Pregunta | Respuesta |
|----------|-----------|
| ¿El check-out anterior será automáticamente esa fecha? | **SÍ, automáticamente** |
| ¿Cómo se manejan las horas? | **Backend preserva horas originales por defecto, o usa las proporcionadas** |
| ¿Lo maneja el backend o frontend? | **100% BACKEND** - Frontend solo envía fechas |
| ¿Necesito calcular algo en el frontend? | **NO** - Solo envía `change_start_date` y `change_end_date` |
| ¿Puedo especificar horas diferentes? | **SÍ** - Opcional: `check_in_hour`, `check_in_minute`, etc. |

---

## 💡 Recomendación para tu Frontend

```javascript
// Función simplificada - El backend hace todo el trabajo
const changeRoom = async (bookingId, lineId, newRoomId, changeStartDate, changeEndDate) => {
  const payload = {
    booking_line_id: lineId,
    new_room_id: newRoomId,
    change_start_date: changeStartDate,  // "2024-11-11"
    change_end_date: changeEndDate       // "2024-11-14"
    // No necesitas calcular nada más, el backend lo hace
  };

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

  return await response.json();
};

// Uso super simple
await changeRoom(123, 456, 11, "2024-11-11", "2024-11-14");
// El backend:
// - Modifica check-out original a 11/11 automáticamente
// - Crea nueva reserva del 11/11 al 14/11
// - Preserva horas automáticamente
// - Conecta ambas reservas
```

**¡Es así de simple!** 🎉

