# ⏰ Cómo Especificar Horas Exactas en el Cambio de Habitación

## ✅ **PROBLEMA SOLUCIONADO**

El código del wizard ahora **SÍ usa las horas y minutos** que envías desde el frontend.

---

## 📋 **Formas de Especificar Horas Exactas**

### **Método 1: Horas Separadas (RECOMENDADO)**

Envía las horas y minutos por separado:

```javascript
const payload = {
  booking_line_id: 456,
  new_room_id: 11,
  change_start_date: "2024-11-11",
  change_end_date: "2024-11-14",
  
  // ⏰ HORAS EXACTAS para la NUEVA reserva
  check_in_hour: 15,        // 15:00 (3:00 PM)
  check_in_minute: 30,      // 15:30
  check_out_hour: 12,       // 12:00 (12:00 PM)
  check_out_minute: 45      // 12:45
};
```

**Resultado:**
- ✅ Nueva reserva check-in: **11/11/2024 a las 15:30**
- ✅ Nueva reserva check-out: **14/11/2024 a las 12:45**
- ✅ Reserva original check-out: **11/11/2024 a las 11:00** (hora original preservada)

---

### **Método 2: DateTime Completo**

Envía el datetime completo como string:

```javascript
const payload = {
  booking_line_id: 456,
  new_room_id: 11,
  change_start_datetime: "2024-11-11 15:30:00",  // Incluye hora exacta
  change_end_datetime: "2024-11-14 12:45:00"     // Incluye hora exacta
};
```

**Resultado:**
- ✅ Nueva reserva check-in: **11/11/2024 a las 15:30**
- ✅ Nueva reserva check-out: **14/11/2024 a las 12:45**

---

### **Método 3: Solo Fechas (Sin Horas)**

Si NO envías horas, se usan las horas originales:

```javascript
const payload = {
  booking_line_id: 456,
  new_room_id: 11,
  change_start_date: "2024-11-11",  // Solo fecha
  change_end_date: "2024-11-14"     // Solo fecha
  // No hay check_in_hour, check_in_minute, etc.
};
```

**Resultado:**
- ✅ Nueva reserva check-in: **11/11/2024 a las 14:00** (hora original de check-in)
- ✅ Nueva reserva check-out: **14/11/2024 a las 11:00** (hora original de check-out)

---

## 🔧 **Cómo Funciona el Código (Después del Fix)**

### **En el API (`change_room.py`):**

```python
# Extrae las horas del payload
check_in_hour = payload.get('check_in_hour')
check_in_minute = payload.get('check_in_minute')
check_out_hour = payload.get('check_out_hour')
check_out_minute = payload.get('check_out_minute')

# Pasa las horas al contexto del wizard
wizard_ctx = {
    'change_start_hour': change_start_hour,      # 15
    'change_start_minute': change_start_minute,  # 30
    'change_end_hour': change_end_hour,          # 12
    'change_end_minute': change_end_minute,      # 45
}

wizard = request.env['hotel.booking.line.change.room.wizard'].with_context(wizard_ctx).create(wizard_vals)
```

### **En el Wizard (`change_room_wizard.py` - ACTUALIZADO):**

```python
# Obtener horas del contexto o usar las originales
change_start_hour = self.env.context.get('change_start_hour')
change_start_minute = self.env.context.get('change_start_minute')

if change_start_hour is not None and new_checkin:
    # ✅ USAR HORAS PROPORCIONADAS
    new_checkin = new_checkin.replace(
        hour=int(change_start_hour),              # 15
        minute=int(change_start_minute) if change_start_minute is not None else 0,  # 30
        second=0
    )
elif hasattr(booking.check_in, 'time') and new_checkin:
    # Usar horas originales si no se proporcionaron
    new_checkin = new_checkin.replace(
        hour=booking.check_in.hour,
        minute=booking.check_in.minute, 
        second=booking.check_in.second
    )
```

---

## 📝 **Ejemplos Completos para React**

### **Ejemplo 1: Horas Exactas Específicas**

```javascript
const applyRoomChangeWithExactTime = async (bookingId, lineId, newRoomId, startDate, endDate, startTime, endTime) => {
  const payload = {
    booking_line_id: lineId,
    new_room_id: newRoomId,
    change_start_date: startDate,      // "2024-11-11"
    change_end_date: endDate,          // "2024-11-14"
    
    // Horas exactas
    check_in_hour: startTime.hour,           // 15
    check_in_minute: startTime.minute,       // 30
    check_out_hour: endTime.hour,            // 12
    check_out_minute: endTime.minute         // 45
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

// Uso
const result = await applyRoomChangeWithExactTime(
  123, 
  456, 
  11, 
  "2024-11-11", 
  "2024-11-14",
  { hour: 15, minute: 30 },  // Check-in a las 15:30
  { hour: 12, minute: 45 }   // Check-out a las 12:45
);
```

---

### **Ejemplo 2: Desde un Input de Tipo Time**

```javascript
const RoomChangeForm = () => {
  const [formData, setFormData] = useState({
    startDate: '',
    endDate: '',
    startTime: '15:30',  // Formato HH:MM
    endTime: '12:45'
  });

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Convertir tiempo string "15:30" a hour y minute
    const [startHour, startMinute] = formData.startTime.split(':').map(Number);
    const [endHour, endMinute] = formData.endTime.split(':').map(Number);

    const payload = {
      booking_line_id: 456,
      new_room_id: 11,
      change_start_date: formData.startDate,
      change_end_date: formData.endDate,
      check_in_hour: startHour,      // 15
      check_in_minute: startMinute,  // 30
      check_out_hour: endHour,       // 12
      check_out_minute: endMinute    // 45
    };

    // Enviar al API
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
    console.log('Horas aplicadas:', {
      check_in: `${formData.startDate} ${formData.startTime}`,
      check_out: `${formData.endDate} ${formData.endTime}`
    });
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="date"
        value={formData.startDate}
        onChange={(e) => setFormData({...formData, startDate: e.target.value})}
      />
      <input
        type="time"
        value={formData.startTime}
        onChange={(e) => setFormData({...formData, startTime: e.target.value})}
      />
      <input
        type="date"
        value={formData.endDate}
        onChange={(e) => setFormData({...formData, endDate: e.target.value})}
      />
      <input
        type="time"
        value={formData.endTime}
        onChange={(e) => setFormData({...formData, endTime: e.target.value})}
      />
      <button type="submit">Aplicar Cambio</button>
    </form>
  );
};
```

---

### **Ejemplo 3: Componente Completo con Selectores de Hora**

```jsx
import React, { useState } from 'react';

const RoomChangeWithTimeSelector = ({ bookingId, lineId, newRoomId }) => {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [startHour, setStartHour] = useState(null);
  const [startMinute, setStartMinute] = useState(null);
  const [endHour, setEndHour] = useState(null);
  const [endMinute, setEndMinute] = useState(null);
  const [useCustomTime, setUseCustomTime] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();

    const payload = {
      booking_line_id: lineId,
      new_room_id: newRoomId,
      change_start_date: startDate,
      change_end_date: endDate
    };

    // Solo agregar horas si se especificaron
    if (useCustomTime) {
      if (startHour !== null) {
        payload.check_in_hour = parseInt(startHour);
        payload.check_in_minute = startMinute !== null ? parseInt(startMinute) : 0;
      }
      if (endHour !== null) {
        payload.check_out_hour = parseInt(endHour);
        payload.check_out_minute = endMinute !== null ? parseInt(endMinute) : 0;
      }
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

      const result = await response.json();
      
      if (result.success) {
        alert(`Cambio aplicado exitosamente. Check-in: ${startDate} ${startHour || 'hora original'}, Check-out: ${endDate} ${endHour || 'hora original'}`);
      }
    } catch (error) {
      console.error('Error:', error);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label>
          Fecha Inicio del Cambio:
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            required
          />
        </label>
      </div>

      <div>
        <label>
          Fecha Fin en Nueva Habitación:
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            required
          />
        </label>
      </div>

      <div>
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
        <>
          <div>
            <label>
              Hora Check-in (0-23):
              <input
                type="number"
                min="0"
                max="23"
                value={startHour ?? ''}
                onChange={(e) => setStartHour(e.target.value ? parseInt(e.target.value) : null)}
              />
            </label>
            <label>
              Minuto (0-59):
              <input
                type="number"
                min="0"
                max="59"
                value={startMinute ?? ''}
                onChange={(e) => setStartMinute(e.target.value ? parseInt(e.target.value) : null)}
              />
            </label>
          </div>

          <div>
            <label>
              Hora Check-out (0-23):
              <input
                type="number"
                min="0"
                max="23"
                value={endHour ?? ''}
                onChange={(e) => setEndHour(e.target.value ? parseInt(e.target.value) : null)}
              />
            </label>
            <label>
              Minuto (0-59):
              <input
                type="number"
                min="0"
                max="59"
                value={endMinute ?? ''}
                onChange={(e) => setEndMinute(e.target.value ? parseInt(e.target.value) : null)}
              />
            </label>
          </div>
        </>
      )}

      <button type="submit">Aplicar Cambio de Habitación</button>
    </form>
  );
};

export default RoomChangeWithTimeSelector;
```

---

## 🎯 **Resumen de Campos**

| Campo | Tipo | Rango | Descripción |
|-------|------|-------|-------------|
| `check_in_hour` | integer | 0-23 | Hora de check-in de la nueva reserva |
| `check_in_minute` | integer | 0-59 | Minuto de check-in de la nueva reserva |
| `check_out_hour` | integer | 0-23 | Hora de check-out de la nueva reserva |
| `check_out_minute` | integer | 0-59 | Minuto de check-out de la nueva reserva |

**Nota:** Si NO envías estos campos, el sistema usa las horas originales de la reserva automáticamente.

---

## ✅ **Validación de Horas**

El código valida automáticamente:
- ✅ Horas entre 0-23
- ✅ Minutos entre 0-59
- ✅ Si no se proporciona minuto, usa 0 por defecto

---

## 📊 **Ejemplo de Respuesta**

Cuando envías horas exactas, la respuesta incluye las horas aplicadas:

```json
{
  "success": true,
  "data": {
    "new_reserva": {
      "id": 124,
      "check_in": "2024-11-11 15:30:00",  // ← Hora exacta aplicada
      "check_out": "2024-11-14 12:45:00", // ← Hora exacta aplicada
      "check_in_hour": 15,
      "check_in_minute": 30,
      "check_out_hour": 12,
      "check_out_minute": 45
    }
  }
}
```

---

## 🎉 **Ahora SÍ Funciona Correctamente**

El código del wizard ha sido actualizado para **usar las horas exactas** que envías desde el frontend. 

**Antes:** Ignoraba las horas del contexto  
**Ahora:** ✅ Usa las horas proporcionadas, o las horas originales si no se especifican

¡Ya puedes especificar horas exactas con minutos! 🕐

