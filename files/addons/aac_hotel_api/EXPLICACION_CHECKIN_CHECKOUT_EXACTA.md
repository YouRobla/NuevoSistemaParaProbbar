# ⏰ Explicación EXACTA: Check-in y Check-out en Cambio de Habitación

## 🤔 Tu Pregunta:

**¿El check-in de la nueva habitación será el mismo que el check-out de la anterior?**

## 📋 Respuesta Corta:

**NO necesariamente.** Depende de si envías horas o no. Te explico **exactamente** cómo funciona:

---

## 🔍 Cómo Funciona EXACTAMENTE

### **Lo que SÍ es automático:**

✅ **Las FECHAS coinciden:**
- El **check-out de la reserva anterior** = `change_start_date` (misma fecha)
- El **check-in de la nueva reserva** = `change_start_date` (misma fecha)

### **Lo que NO es automático (depende de ti):**

❌ **Las HORAS NO necesariamente coinciden:**
- Depende de si envías horas o no
- Si **NO envías horas** → Usa horas originales diferentes
- Si **envías horas** → Usa las horas que especifiques

---

## 📊 Ejemplo Paso a Paso

### **Escenario:**
```
Reserva Original:
- Check-in:  10/11/2024 a las 14:00 (2:00 PM)
- Check-out: 15/11/2024 a las 11:00 (11:00 AM)

Cambio el día: 12/11/2024
```

---

## 🎯 Caso 1: NO Envías Horas

### **Código Frontend:**

```javascript
const payload = {
  booking_line_id: 456,
  new_room_id: 11,
  change_start_date: "2024-11-12",
  change_end_date: "2024-11-15"
  // NO hay check_in_hour, check_in_minute, etc.
};
```

### **¿Qué hace el Backend?**

#### **Reserva Original (Modificada):**

```python
# Código línea 194-200
original_end_date = change_start_date  # 12/11/2024 (fecha del cambio)
new_checkout = fields.Datetime.to_datetime(original_end_date)  # 12/11 00:00:00

# PRESERVA la HORA ORIGINAL de check-out
new_checkout = new_checkout.replace(
    hour=booking.check_out.hour,      # 11 (hora original)
    minute=booking.check_out.minute,   # 0 (hora original)
    second=booking.check_out.second
)
```

**Resultado:**
- ✅ Check-out reserva original: **12/11/2024 a las 11:00** (hora original preservada)

#### **Nueva Reserva (Creada):**

```python
# Código línea 234-247
new_checkin = fields.Datetime.to_datetime(change_start_date)  # 12/11 00:00:00

# Como NO hay horas en el contexto, usa horas ORIGINALES de check-in
new_checkin = new_checkin.replace(
    hour=booking.check_in.hour,      # 14 (hora original de check-in)
    minute=booking.check_in.minute,   # 0 (hora original de check-in)
    second=booking.check_in.second
)
```

**Resultado:**
- ✅ Check-in nueva reserva: **12/11/2024 a las 14:00** (hora original de check-in)

### **Resultado Final:**

```
Reserva Original (Modificada):
- Check-out: 12/11/2024 a las 11:00  ← Hora original de check-out

Nueva Reserva:
- Check-in:  12/11/2024 a las 14:00  ← Hora original de check-in

❌ NO COINCIDEN LAS HORAS
✅ SÍ COINCIDEN LAS FECHAS (ambas 12/11)
```

**Intervalo entre check-out y check-in:** 3 horas (de 11:00 a 14:00)

---

## 🎯 Caso 2: SÍ Envías Horas Específicas

### **Código Frontend:**

```javascript
const payload = {
  booking_line_id: 456,
  new_room_id: 11,
  change_start_date: "2024-11-12",
  change_end_date: "2024-11-15",
  
  // Horas específicas
  check_in_hour: 12,      // Check-in nueva a las 12:00
  check_in_minute: 0,
  check_out_hour: 11,
  check_out_minute: 0
};
```

### **¿Qué hace el Backend?**

#### **Reserva Original (Modificada):**

```python
# Código línea 194-200 (NO cambia, siempre usa hora original)
original_end_date = change_start_date  # 12/11/2024
new_checkout = fields.Datetime.to_datetime(original_end_date)

# PRESERVA la HORA ORIGINAL de check-out
new_checkout = new_checkout.replace(
    hour=booking.check_out.hour,      # 11 (hora original)
    minute=booking.check_out.minute,   # 0
    second=booking.check_out.second
)
```

**Resultado:**
- ✅ Check-out reserva original: **12/11/2024 a las 11:00** (hora original)

#### **Nueva Reserva (Creada):**

```python
# Código línea 234-240
new_checkin = fields.Datetime.to_datetime(change_start_date)  # 12/11 00:00:00

# Como SÍ hay horas en el contexto, usa las PROPORCIONADAS
change_start_hour = self.env.context.get('change_start_hour')  # 12
change_start_minute = self.env.context.get('change_start_minute')  # 0

new_checkin = new_checkin.replace(
    hour=int(change_start_hour),      # 12 (hora que enviaste)
    minute=int(change_start_minute),  # 0 (minuto que enviaste)
    second=0
)
```

**Resultado:**
- ✅ Check-in nueva reserva: **12/11/2024 a las 12:00** (hora que enviaste)

### **Resultado Final:**

```
Reserva Original (Modificada):
- Check-out: 12/11/2024 a las 11:00  ← Hora original

Nueva Reserva:
- Check-in:  12/11/2024 a las 12:00  ← Hora que enviaste

❌ NO COINCIDEN LAS HORAS
✅ SÍ COINCIDEN LAS FECHAS (ambas 12/11)
```

**Intervalo entre check-out y check-in:** 1 hora (de 11:00 a 12:00)

---

## 🎯 Caso 3: Envías Horas para que COINCIDAN

### **Si quieres que el check-in de la nueva sea IGUAL al check-out de la anterior:**

Primero necesitas saber la hora de check-out de la reserva original:

```javascript
// 1. Obtener reserva original
const reservaOriginal = await getBooking(123);
const checkoutOriginal = new Date(reservaOriginal.check_out);

// 2. Extraer hora y minuto
const checkoutHour = checkoutOriginal.getHours();      // 11
const checkoutMinute = checkoutOriginal.getMinutes();  // 0

// 3. Aplicar cambio usando la MISMA hora de check-out
const payload = {
  booking_line_id: 456,
  new_room_id: 11,
  change_start_date: "2024-11-12",
  change_end_date: "2024-11-15",
  
  // Usar la MISMA hora de check-out para el check-in
  check_in_hour: checkoutHour,      // 11 (misma que check-out)
  check_in_minute: checkoutMinute,  // 0 (mismo que check-out)
  check_out_hour: 11,
  check_out_minute: 0
};

const resultado = await changeRoom(123, payload);
```

### **Resultado:**

```
Reserva Original (Modificada):
- Check-out: 12/11/2024 a las 11:00

Nueva Reserva:
- Check-in:  12/11/2024 a las 11:00  ← MISMA HORA

✅ SÍ COINCIDEN TANTO FECHA COMO HORA
```

---

## 📋 Resumen Visual

### **Comparación de los 3 Casos:**

```
┌─────────────────────────────────────────────────────────┐
│ CASO 1: Sin horas especificadas                        │
├─────────────────────────────────────────────────────────┤
│ Reserva Original: 12/11 a las 11:00                    │
│ Nueva Reserva:    12/11 a las 14:00                    │
│                                                         │
│ ❌ Horas NO coinciden                                  │
│ ✅ Fechas SÍ coinciden                                 │
│ ⏱️ Intervalo: 3 horas                                 │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ CASO 2: Con horas diferentes                           │
├─────────────────────────────────────────────────────────┤
│ Reserva Original: 12/11 a las 11:00                    │
│ Nueva Reserva:    12/11 a las 12:00 (especificaste)    │
│                                                         │
│ ❌ Horas NO coinciden                                  │
│ ✅ Fechas SÍ coinciden                                 │
│ ⏱️ Intervalo: 1 hora                                  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ CASO 3: Con horas iguales (tú las haces coincidir)     │
├─────────────────────────────────────────────────────────┤
│ Reserva Original: 12/11 a las 11:00                    │
│ Nueva Reserva:    12/11 a las 11:00 (igual que check-out) │
│                                                         │
│ ✅ Horas SÍ coinciden                                  │
│ ✅ Fechas SÍ coinciden                                 │
│ ⏱️ Intervalo: 0 horas (transición inmediata)          │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 Código Helper para Hacer Coincidir

```javascript
// Función helper para hacer que el check-in coincida con el check-out anterior
const changeRoomWithMatchingCheckout = async (bookingId, changeData) => {
  // 1. Obtener reserva actual para saber su hora de check-out
  const reservaActual = await getBooking(bookingId);
  const checkoutDate = new Date(reservaActual.check_out);
  
  // 2. Extraer hora y minuto del check-out actual
  const checkoutHour = checkoutDate.getHours();
  const checkoutMinute = checkoutDate.getMinutes();
  
  // 3. Aplicar cambio usando la misma hora de check-out para el check-in
  return await changeRoom(bookingId, {
    ...changeData,
    // Hacer que el check-in de la nueva reserva sea igual al check-out de la anterior
    check_in_hour: checkoutHour,      // Misma hora
    check_in_minute: checkoutMinute   // Mismo minuto
  });
};

// Uso
const resultado = await changeRoomWithMatchingCheckout(123, {
  lineId: 456,
  newRoomId: 11,
  startDate: "2024-11-12",
  endDate: "2024-11-15"
});

// Resultado:
// - Check-out anterior: 12/11 a las 11:00
// - Check-in nueva:     12/11 a las 11:00  ← Coinciden
```

---

## 📝 Reglas Exactas del Backend

### **Para el Check-out de la Reserva Original:**

```python
# SIEMPRE usa:
original_end_date = change_start_date  # Misma FECHA
hora = booking.check_out.hour          # HORA ORIGINAL (no cambia)
minuto = booking.check_out.minute      # MINUTO ORIGINAL (no cambia)
```

**NO puedes cambiar** la hora de check-out de la reserva original. Siempre usa la hora original.

### **Para el Check-in de la Nueva Reserva:**

```python
# FECHA:
new_checkin_date = change_start_date  # Misma FECHA que check-out anterior

# HORA:
if horas_proporcionadas_en_contexto:
    hora = horas_que_enviaste
else:
    hora = booking.check_in.hour  # Hora original de check-in
```

**Puedes controlar** la hora de check-in de la nueva reserva enviando `check_in_hour` y `check_in_minute`.

---

## ✅ Respuesta Final a tu Pregunta

**¿El check-in de la nueva habitación será el check-out del anterior?**

**NO automáticamente.** Pero puedes hacerlo:

1. **Automático (sin horas):** El check-in usa la hora original de check-in, NO la de check-out
2. **Manual (con horas):** Puedes hacer que coincidan enviando `check_in_hour` igual a la hora de check-out anterior

**Las FECHAS siempre coinciden** (ambas son `change_start_date`), pero las **HORAS dependen de ti**.

---

## 🎯 Ejemplo Práctico Completo

```javascript
// Escenario: Cambio el 12/11
// Reserva original check-out: 15/11 a las 11:00

// Opción A: NO especificar horas (automático)
const cambio1 = await changeRoom(123, {
  lineId: 456,
  newRoomId: 11,
  startDate: "2024-11-12",
  endDate: "2024-11-15"
});
// Resultado:
// - Check-out anterior: 12/11 a las 11:00 (hora original)
// - Check-in nueva:     12/11 a las 14:00 (hora original check-in)
// ❌ NO coinciden

// Opción B: Especificar para que coincidan
const reserva = await getBooking(123);
const checkoutHour = new Date(reserva.check_out).getHours(); // 11

const cambio2 = await changeRoom(123, {
  lineId: 456,
  newRoomId: 11,
  startDate: "2024-11-12",
  endDate: "2024-11-15",
  check_in_hour: checkoutHour,      // 11 (igual que check-out)
  check_in_minute: 0
});
// Resultado:
// - Check-out anterior: 12/11 a las 11:00
// - Check-in nueva:     12/11 a las 11:00
// ✅ SÍ coinciden
```

---

**Espero que esto aclare exactamente cómo funciona. ¿Tienes alguna otra pregunta?** 🎯

