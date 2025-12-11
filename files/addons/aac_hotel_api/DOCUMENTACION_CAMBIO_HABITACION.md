# 📋 Documentación: Lógica de Cambio de Habitación

## 📍 Ubicación en el Código

### API Endpoints (`aac_hotel_api`)
- **Archivo**: `Hotel/aac_hotel_api/controllers/change_room.py`
- **Controlador**: `ChangeRoomApiController`

### Lógica de Negocio (Backend)
- **Archivo**: `AAC/hotel_management_system_extension/wizard/change_room_wizard.py`
- **Modelo**: `hotel.booking.line.change.room.wizard`
- **Método principal**: `action_confirm()`

---

## 🔄 Flujo Completo de Cambio de Habitación

### **Paso 1: Obtener Opciones de Cambio**

**Endpoint API:**
```
GET/POST /api/hotel/reserva/<booking_id>/change_room/options
```

**¿Qué hace?**
1. Valida que la reserva existe y obtiene la línea de reserva (`booking_line_id`)
2. Crea un wizard temporal (`hotel.booking.line.change.room.wizard`) en modo `new()` (no guardado)
3. Calcula habitaciones disponibles para las fechas propuestas
4. Retorna información de:
   - Habitación actual (nombre, código, capacidad, precio)
   - Habitaciones disponibles para cambio
   - Fechas propuestas (desde hoy hasta el final de la reserva)
   - Total de noches estimadas
   - Precio estimado del cambio

**Respuesta de ejemplo:**
```json
{
  "success": true,
  "data": {
    "defaults": {
      "booking_id": 123,
      "booking_line_id": 456,
      "current_room_id": 10,
      "current_room_name": "Habitación 101",
      "change_start_date": "2024-01-15",
      "change_end_date": "2024-01-20",
      "total_nights": 5,
      "estimated_total": 500.00
    },
    "available_rooms": [
      {
        "id": 11,
        "name": "Habitación 102",
        "code": "RM102",
        "price": 100.00
      }
    ]
  }
}
```

---

### **Paso 2: Aplicar el Cambio de Habitación**

**Endpoint API:**
```
POST /api/hotel/reserva/<booking_id>/change_room
```

**Payload requerido:**
```json
{
  "booking_line_id": 456,
  "new_room_id": 11,
  "change_start_date": "2024-01-15",  // o "2024-01-15 14:00:00"
  "change_end_date": "2024-01-20",    // o "2024-01-20 11:00:00"
  "use_custom_price": false,          // opcional
  "custom_price": 90.00,              // solo si use_custom_price = true
  "note": "Cambio solicitado por el cliente",
  // Opcional: horas separadas
  "check_in_hour": 14,
  "check_in_minute": 0,
  "check_out_hour": 11,
  "check_out_minute": 0
}
```

**¿Qué hace el backend (`action_confirm()`)?**

#### **1. Validaciones Iniciales**
- ✅ Verifica que las fechas sean válidas
- ✅ Valida que `change_start_date < change_end_date`
- ✅ Verifica que la fecha de inicio esté dentro del período original
- ✅ Confirma que la nueva habitación sea diferente a la actual
- ✅ **Verifica disponibilidad** de la nueva habitación en el período solicitado
- ✅ Valida precio personalizado si se usa

#### **2. Modificación de la Reserva Original**

**Escenario A: Cambio parcial (original_days > 0)**
```
Reserva Original: 2024-01-10 → 2024-01-20 (10 días)
Cambio desde: 2024-01-15
```

**Lo que hace:**
- ✅ Modifica `check_out` de la reserva original a `change_start_date` (1 día antes del cambio)
- ✅ Actualiza `booking_days` de la línea original al nuevo número de días
- ✅ **Mantiene estado `checkin`** para continuar la estancia
- ✅ Establece `connected_booking_id` apuntando a la nueva reserva
- ✅ Marca `is_room_change_origin = True`

**Resultado:**
- Reserva Original: 2024-01-10 → 2024-01-15 (5 días) - Estado: `checkin`

**Escenario B: Cambio desde el inicio (original_days = 0)**
- ✅ Cancela la reserva original (`status_bar = 'cancelled'`)
- ✅ Publica mensaje en el chatter explicando la cancelación

#### **3. Creación de Nueva Reserva**

**Datos copiados de la reserva original:**
- ✅ `partner_id` (cliente)
- ✅ `hotel_id`
- ✅ `user_id` (responsable)
- ✅ `company_id`
- ✅ `currency_id`
- ✅ `pricelist_id`
- ✅ `agent_id` y comisiones (si aplica)
- ✅ Horas de check-in y check-out originales

**Datos específicos de la nueva reserva:**
- ✅ `check_in`: `change_start_date` con hora original
- ✅ `check_out`: `change_end_date` con hora original
- ✅ `status_bar`: `confirmed` inicialmente, luego `checkin`
- ✅ `split_from_booking_id`: ID de la reserva original
- ✅ `connected_booking_id`: ID de la reserva original (conexión bidireccional)
- ✅ `is_room_change_destination = True`
- ✅ `origin`: "Original - Cambio habitación"
- ✅ `description`: Incluye nota sobre el cambio

#### **4. Creación de Nueva Línea de Reserva**

**Para la nueva habitación:**
- ✅ `product_id`: Nueva habitación seleccionada
- ✅ `booking_days`: Número de noches (`change_end - change_start`)
- ✅ `price`: Precio unitario (personalizado o precio de lista de la habitación)
- ✅ `discount`: Copiado de la línea original
- ✅ `tax_ids`: Copiado de la línea original

#### **5. Copia de Huéspedes**

- ✅ Copia todos los `guest_info_ids` de la línea original a la nueva línea
- ✅ Mantiene: nombre, edad, género, `partner_id`

#### **6. Transferencia de Servicios Manuales**

- ✅ **MUEVE** (no copia) servicios manuales de la reserva original a la nueva
- ✅ Busca servicios con `service_id.name = 'Servicio Manual'`
- ✅ Actualiza `booking_id` del servicio a la nueva reserva

#### **7. Gestión de Facturación (Órdenes de Venta)**

**Estrategia: Transferencia completa**

- ✅ **TRANSFIERE** todas las órdenes de venta (`sale.order`) de la original a la nueva
- ✅ Esto incluye:
  - Servicios adicionales (early check-in, late check-out)
  - Servicios manuales ya transferidos
  - Cualquier otro producto/servicio facturado

**Si no hay órdenes de venta existentes:**
- ✅ Crea una nueva orden de venta para la nueva reserva
- ✅ Agrega línea de producto para la nueva habitación

**Importante:**
- ❌ **NO** copia cargos adicionales (`early_checkin_charge`, `late_checkout_charge`) a la nueva reserva
- ✅ Estos se mantienen solo en la reserva original (ya están facturados)
- ✅ Solo se factura la nueva habitación en el período de cambio

#### **8. Mensajería (Chatter)**

**En la reserva original:**
```
"Cambio de habitación aplicado. Reserva original modificada para terminar el 15/01/2024 (estado: CHECK-IN).
Permanece 5 noche(s) en Habitación 101.
Nueva reserva creada: [Link a nueva reserva]"
```

**En la nueva reserva:**
```
"Nueva reserva creada por cambio de habitación desde reserva original: [Link].
Período: 15/01/2024 a 20/01/2024 (5 noche(s)) en Habitación 102."
```

**Si se extendió la reserva:**
```
"⭐ EXTENSIÓN: La reserva se extendió 2 día(s) adicional(es) más allá de la fecha original"
```

#### **9. Respuesta de la API**

```json
{
  "success": true,
  "message": "Cambio de habitación aplicado correctamente.",
  "data": {
    "reserva_id": 123,
    "action": { ... },
    "new_reserva": {
      "id": 124,
      "sequence_id": "RES-2024-001",
      "check_in": "2024-01-15 14:00:00",
      "check_out": "2024-01-20 11:00:00",
      "check_in_hour": 14,
      "check_in_minute": 0,
      "check_out_hour": 11,
      "check_out_minute": 0,
      "status_bar": "checkin"
    }
  }
}
```

---

## 🔗 Campos de Conexión entre Reservas

El sistema utiliza varios campos para mantener la relación entre reservas:

### **En `hotel.booking`:**

1. **`split_from_booking_id`** (Many2one)
   - Reserva original de la cual se dividió esta reserva
   - Solo en la **nueva reserva** apunta a la original

2. **`connected_booking_id`** (Many2one)
   - **Conexión bidireccional** entre reservas relacionadas
   - Reserva original → Nueva reserva
   - Nueva reserva → Reserva original

3. **`is_room_change_origin`** (Boolean)
   - `True` en la reserva original que dio origen al cambio

4. **`is_room_change_destination`** (Boolean)
   - `True` en la nueva reserva creada por el cambio

**Ejemplo:**
```
Reserva Original (ID: 123)
├── connected_booking_id = 124
├── is_room_change_origin = True
└── split_from_booking_id = False

Nueva Reserva (ID: 124)
├── connected_booking_id = 123
├── is_room_change_destination = True
└── split_from_booking_id = 123
```

---

## ✅ Validaciones de Disponibilidad

### **Método: `_is_room_available()`**

**¿Qué verifica?**
1. Busca `hotel.booking.line` que:
   - Usen la misma habitación (`product_id`)
   - Pertenezcan a reservas **no canceladas** (`status_bar NOT IN ['cancelled', 'no_show']`)
   - **No** sean de la reserva actual (`booking_id != self.booking_id.id`)
   - Tengan solapamiento de fechas:
     - `booking.check_in < change_end_date`
     - `booking.check_out > change_start_date`

2. Si encuentra solapamiento → Habitación **NO disponible**
3. Si no encuentra solapamiento → Habitación **disponible**

**Nota importante:**
- La validación **NO excluye** la reserva actual de la búsqueda, pero sí verifica que las otras reservas no se solapen
- Permite que una habitación esté "ocupada" por la misma reserva durante el cambio

---

## 💰 Gestión de Precios

### **Precio por Defecto**
- Usa el `list_price` de la nueva habitación
- Multiplica por el número de noches

### **Precio Personalizado**
- Si `use_custom_price = True`:
  - Usa `custom_price` proporcionado
  - Permite precio de `0.00` (cambio gratuito)
  - Si no se proporciona precio → Error de validación

### **Precio Original de la Línea**
- Se establece `original_price` en la nueva línea con el precio de lista de la plantilla de producto

---

## 🎯 Casos Especiales

### **1. Extensión de Reserva**
Si `change_end_date > check_out original`:
- ✅ Permite extender la estancia más allá de la fecha original
- ✅ Solo se facturan las noches adicionales en la nueva habitación
- ✅ Se muestra mensaje de extensión en el chatter

### **2. Cambio Inmediato (desde check-in)**
Si `change_start_date = check_in original`:
- ✅ Cancela la reserva original completamente
- ✅ Crea nueva reserva desde el inicio

### **3. Cambio con Múltiples Líneas**
Si la reserva tiene múltiples líneas (múltiples habitaciones):
- ✅ Requiere especificar `booking_line_id` explícitamente
- ✅ Solo modifica la línea especificada
- ✅ Las otras líneas permanecen intactas en la reserva original

### **4. Servicios y Facturación**
- ✅ Servicios manuales se **mueven** (no duplican)
- ✅ Órdenes de venta se **transfieren** completamente
- ✅ Early check-in / Late check-out NO se copian (pertenecen a la original)

---

## 🔍 Búsqueda de Habitaciones Disponibles

### **Método: `_compute_available_rooms()`**

**Algoritmo:**
1. Obtiene todas las habitaciones del hotel (`product.product` con `is_room_type = True`)
2. Para cada habitación:
   - Llama a `_is_room_available()` con las fechas propuestas
   - Si está disponible → Agrega a la lista
3. Retorna lista de habitaciones disponibles

**Parámetros considerados:**
- `change_start_date`
- `change_end_date`
- `hotel_id` de la reserva original

---

## ⏰ Manejo de Horas y Minutos

### **¿El sistema maneja horas y minutos?**

**¡SÍ!** El sistema **SÍ maneja horas y minutos** para check-in y check-out en el cambio de habitación.

### **Cómo se manejan las horas:**

#### **1. En el API (`change_room.py`)**

El endpoint acepta horas de **3 formas diferentes**:

**Opción A: Horas separadas (Recomendado)**
```json
{
  "change_start_date": "2024-01-15",
  "change_end_date": "2024-01-20",
  "check_in_hour": 14,
  "check_in_minute": 0,
  "check_out_hour": 11,
  "check_out_minute": 0
}
```

**Opción B: DateTime completo en string**
```json
{
  "change_start_datetime": "2024-01-15 14:00:00",
  "change_end_datetime": "2024-01-20 11:00:00"
}
```

**Opción C: Solo fechas (sin horas)**
```json
{
  "change_start_date": "2024-01-15",
  "change_end_date": "2024-01-20"
}
```
Si no se proporcionan horas → **Usa las horas de la reserva original**

#### **2. Prioridad de Horas**

El sistema sigue este orden de prioridad:
1. **Horas separadas** (`check_in_hour`, `check_in_minute`) - **Mayor prioridad**
2. **DateTime completo** (`change_start_datetime` con horas incluidas)
3. **Horas de la reserva original** (si no se proporcionan horas)

**Código relevante:**
```python
# Prioridad: horas separadas > change_start_datetime > change_start_date
if start_datetime_str and check_in_hour is not None:
    # Construir datetime desde fecha + horas separadas
    start_datetime = datetime.combine(
        start_date_obj,
        time(hour=int(check_in_hour), minute=int(check_in_minute) or 0)
    )
```

#### **3. Preservación de Horas en el Wizard**

El wizard recibe las horas a través del **contexto**:
```python
wizard_ctx = {
    'change_start_hour': change_start_hour,      # 14
    'change_start_minute': change_start_minute,  # 0
    'change_end_hour': change_end_hour,          # 11
    'change_end_minute': change_end_minute,      # 0
}
```

#### **4. Creación de Reservas con Horas**

**Reserva Original (modificada):**
- ✅ Preserva la **hora original de check-out**
- ✅ Usa `booking.check_out.hour` y `booking.check_out.minute`
- ✅ Solo cambia la fecha, mantiene la hora

**Nueva Reserva (creada):**
- ✅ Usa las **horas proporcionadas** (o las originales si no se especificaron)
- ✅ Para check-in: `booking.check_in.hour` y `booking.check_in.minute` (o las proporcionadas)
- ✅ Para check-out: `booking.check_out.hour` y `booking.check_out.minute` (o las proporcionadas)

**Código relevante:**
```python
# Crear datetime para la nueva reserva manteniendo las horas
new_checkin = fields.Datetime.to_datetime(change_start)
if hasattr(booking.check_in, 'time') and new_checkin:
    new_checkin = new_checkin.replace(
        hour=booking.check_in.hour,      # Preserva hora original
        minute=booking.check_in.minute,  # Preserva minuto original
        second=booking.check_in.second
    )
```

### **Validaciones de Horas**

#### **1. Validación de Disponibilidad**

El método `_is_room_available()` verifica solapamiento considerando **fechas y horas**:

```python
def _is_room_available(self, room, start_date, end_date):
    overlapping_lines = self.env['hotel.booking.line'].search([
        ('product_id', '=', room.id),
        ('booking_id.status_bar', 'not in', ['cancelled', 'no_show']),
        ('booking_id', '!=', self.booking_id.id),
        ('booking_id.check_in', '<', fields.Datetime.to_datetime(end_date)),
        ('booking_id.check_out', '>', fields.Datetime.to_datetime(start_date)),
    ], limit=1)
    return not bool(overlapping_lines)
```

**Importante:**
- ✅ Compara con `booking.check_in` y `booking.check_out` que **SÍ tienen horas**
- ⚠️ El método recibe solo **fechas** (`start_date`, `end_date`)
- ⚠️ Convierte fechas a datetime usando `fields.Datetime.to_datetime()` (medianoche por defecto)
- ⚠️ **La validación de disponibilidad se hace por día completo**, no por horas específicas

**Nota:** Si las horas son críticas para tu negocio, podrías necesitar mejorar la validación para considerar las horas exactas.

#### **2. Validación de Formato**

El API valida que las horas y minutos sean números válidos:
- ✅ `check_in_hour`: Debe ser entero entre 0-23
- ✅ `check_in_minute`: Debe ser entero entre 0-59
- ✅ Si `check_in_minute` no se proporciona → Usa `0`

**Código de validación:**
```python
# Validar que tenemos un objeto date válido
if not isinstance(start_date_obj, date_type):
    raise UserError('Fecha de inicio inválida.')

# Crear datetime con las horas proporcionadas
start_datetime = datetime.combine(
    start_date_obj,
    time(
        hour=int(check_in_hour),  # Convierte a int
        minute=int(check_in_minute) if check_in_minute is not None else 0
    )
)
```

#### **3. Validación de Orden Temporal**

- ✅ Verifica que `change_start_date < change_end_date`
- ✅ Verifica que `change_start_date` esté dentro del período de la reserva original
- ⚠️ **NO valida** que las horas de check-out sean después de check-in en el mismo día (eso se maneja a nivel de reserva)

### **Ejemplo Completo con Horas**

```javascript
// Solicitud de cambio con horas específicas
const payload = {
  booking_line_id: 456,
  new_room_id: 11,
  change_start_date: "2024-01-15",
  change_end_date: "2024-01-20",
  // Horas específicas para el cambio
  check_in_hour: 14,      // 2:00 PM
  check_in_minute: 30,    // 30 minutos
  check_out_hour: 11,     // 11:00 AM
  check_out_minute: 0,    // 0 minutos
  use_custom_price: false,
  note: "Cambio con horas específicas"
};

// Respuesta con horas confirmadas
{
  "success": true,
  "data": {
    "new_reserva": {
      "id": 124,
      "check_in": "2024-01-15 14:30:00",
      "check_out": "2024-01-20 11:00:00",
      "check_in_hour": 14,
      "check_in_minute": 30,
      "check_out_hour": 11,
      "check_out_minute": 0,
      "status_bar": "checkin"
    }
  }
}
```

### **Casos Especiales de Horas**

#### **Caso 1: Solo Fechas (sin horas)**
```json
{
  "change_start_date": "2024-01-15",
  "change_end_date": "2024-01-20"
}
```
**Resultado:** Usa las horas de la reserva original
- Check-in: Misma hora que la reserva original
- Check-out: Misma hora que la reserva original

#### **Caso 2: Horas Mezcladas**
```json
{
  "change_start_date": "2024-01-15",
  "check_in_hour": 14,
  "check_in_minute": 0,
  "change_end_date": "2024-01-20"
  // No se proporcionan check_out_hour/minute
}
```
**Resultado:**
- Check-in: 14:00 (proporcionado)
- Check-out: Hora original de la reserva

#### **Caso 3: DateTime Completo**
```json
{
  "change_start_datetime": "2024-01-15T14:30:00",
  "change_end_datetime": "2024-01-20T11:00:00"
}
```
**Resultado:** Extrae fechas y horas del datetime
- Check-in: 15/01/2024 14:30:00
- Check-out: 20/01/2024 11:00:00

### **Recomendaciones para Frontend**

1. **Siempre envía horas explícitas** si el usuario las especifica
2. **Si no se especifican horas**, puedes omitirlas y el sistema usará las originales
3. **Validar en frontend** que las horas sean válidas (0-23 para horas, 0-59 para minutos)
4. **Mostrar las horas confirmadas** en la respuesta del API al usuario

---

## 📊 Flujo Visual

```
┌─────────────────────────────────────────────────────────────┐
│  RESERVA ORIGINAL                                           │
│  ID: 123                                                    │
│  Habitación: 101                                            │
│  Fechas: 2024-01-10 → 2024-01-20                           │
│  Estado: checkin                                            │
└─────────────────────────────────────────────────────────────┘
                        │
                        │ Usuario solicita cambio
                        │ desde 2024-01-15 a Habitación 102
                        ▼
        ┌───────────────────────────────┐
        │  VALIDACIONES                 │
        │  ✓ Fechas válidas             │
        │  ✓ Habitación 102 disponible  │
        │  ✓ Precio validado            │
        └───────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 1: MODIFICAR RESERVA ORIGINAL                        │
│  ✓ check_out = 2024-01-15                                  │
│  ✓ booking_days = 5                                        │
│  ✓ connected_booking_id = 124                              │
│  ✓ is_room_change_origin = True                            │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 2: CREAR NUEVA RESERVA                               │
│  ID: 124                                                    │
│  Habitación: 102                                            │
│  Fechas: 2024-01-15 → 2024-01-20                           │
│  Estado: checkin                                            │
│  ✓ split_from_booking_id = 123                             │
│  ✓ connected_booking_id = 123                              │
│  ✓ is_room_change_destination = True                       │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 3: COPIAR DATOS                                      │
│  ✓ Huéspedes                                                │
│  ✓ Servicios manuales (MOVER)                              │
│  ✓ Órdenes de venta (TRANSFERIR)                           │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  RESULTADO FINAL                                            │
│                                                             │
│  Reserva 123: 2024-01-10 → 2024-01-15 (Hab 101)           │
│  Reserva 124: 2024-01-15 → 2024-01-20 (Hab 102)           │
│                                                             │
│  Ambas conectadas y en estado CHECK-IN                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Uso desde Frontend

### **Ejemplo en JavaScript/React:**

```javascript
// 1. Obtener opciones de cambio
const getChangeOptions = async (bookingId, lineId) => {
  const response = await fetch(
    `/api/hotel/reserva/${bookingId}/change_room/options`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'tu-api-key'
      },
      body: JSON.stringify({
        booking_line_id: lineId
      })
    }
  );
  return await response.json();
};

// 2. Aplicar cambio
const applyRoomChange = async (bookingId, changeData) => {
  const response = await fetch(
    `/api/hotel/reserva/${bookingId}/change_room`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'tu-api-key'
      },
      body: JSON.stringify({
        booking_line_id: changeData.lineId,
        new_room_id: changeData.newRoomId,
        change_start_date: changeData.startDate,  // "2024-01-15"
        change_end_date: changeData.endDate,      // "2024-01-20"
        use_custom_price: changeData.useCustomPrice || false,
        custom_price: changeData.customPrice || null,
        note: changeData.note || '',
        // Opcional: horas específicas
        check_in_hour: 14,
        check_in_minute: 0,
        check_out_hour: 11,
        check_out_minute: 0
      })
    }
  );
  return await response.json();
};

// Uso
const handleRoomChange = async () => {
  // Paso 1: Obtener opciones
  const options = await getChangeOptions(123, 456);
  console.log('Habitaciones disponibles:', options.data.available_rooms);
  
  // Paso 2: Aplicar cambio
  const result = await applyRoomChange(123, {
    lineId: 456,
    newRoomId: 11,
    startDate: '2024-01-15',
    endDate: '2024-01-20',
    useCustomPrice: false,
    note: 'Cambio solicitado por el cliente'
  });
  
  if (result.success) {
    console.log('Nueva reserva creada:', result.data.new_reserva);
    // Actualizar UI con nueva reserva
  }
};
```

---

## ⚠️ Consideraciones Importantes

1. **No se pueden deshacer cambios** - Una vez aplicado, se crean nuevas reservas
2. **Facturación unificada** - Las órdenes de venta se transfieren a la nueva reserva
3. **Estado checkin** - Ambas reservas quedan en estado `checkin` para continuar la estancia
4. **Conexión bidireccional** - `connected_booking_id` permite navegar entre reservas relacionadas
5. **Gantt Chart** - Las reservas conectadas se muestran como una estancia continua en el Gantt

---

## 📝 Notas Técnicas

- El wizard usa `invalidate_recordset()` para forzar refresco de campos computados
- Se usa contexto `skip_room_validation=True` al modificar fechas para evitar validaciones estrictas
- Las horas de check-in/check-out se preservan de la reserva original
- El sistema maneja correctamente conversiones entre `date` y `datetime`

