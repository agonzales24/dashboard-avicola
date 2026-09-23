import { sql } from '@vercel/postgres';

export default async function handler(request, response) {
  // Solo permitir peticiones POST
  if (request.method !== 'POST') {
    return response.status(405).json({ error: 'Método no permitido' });
  }

  try {
    const { hembras, machos, inicio, mortHembras, mortMachos } = request.body;

    // Insertar los datos en la tabla 'registro_galpon'
    await sql`
      INSERT INTO registro_galpon 
      (hembras, machos, fecha_inicio, mort_hembras, mort_machos, fecha_registro)
      VALUES 
      (${hembras}, ${machos}, ${inicio}, ${mortHembras}, ${mortMachos}, NOW());
    `;

    return response.status(200).json({ success: true, message: 'Registro insertado correctamente' });
  } catch (error) {
    console.error('Error en la base de datos:', error);
    return response.status(500).json({ error: 'Error interno del servidor al guardar los datos' });
  }
}