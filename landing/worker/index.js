/**
 * EyeExam Waitlist Worker
 * Stores email signups in Cloudflare D1 database
 */

export default {
  async fetch(request, env, _ctx) {
    // CORS headers
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    const url = new URL(request.url);
    const path = url.pathname;

    try {
      // Route: POST /join - Add email to waitlist
      if (path === '/join' && request.method === 'POST') {
        return await handleJoin(request, env, corsHeaders);
      }

      // Route: GET /stats - Get waitlist stats (admin)
      if (path === '/stats' && request.method === 'GET') {
        return await handleStats(request, env, corsHeaders);
      }

      // Route: GET /export - Export emails as CSV (admin)
      if (path === '/export' && request.method === 'GET') {
        return await handleExport(request, env, corsHeaders);
      }

      // 404 for unknown routes
      return jsonResponse({ error: 'Not found' }, 404, corsHeaders);
    } catch {
      return jsonResponse({ error: 'Internal server error' }, 500, corsHeaders);
    }
  },
};

async function handleJoin(request, env, corsHeaders) {
  let body;
  try {
    body = await request.json();
  } catch {
    return jsonResponse({ error: 'Invalid JSON' }, 400, corsHeaders);
  }

  const { email } = body;

  // Validate email
  if (!email || typeof email !== 'string') {
    return jsonResponse({ error: 'Email is required' }, 400, corsHeaders);
  }

  const normalizedEmail = email.toLowerCase().trim();

  if (!isValidEmail(normalizedEmail)) {
    return jsonResponse({ error: 'Invalid email format' }, 400, corsHeaders);
  }

  try {
    // Try D1 first, fall back to KV if D1 not available
    if (env.DB) {
      // Check if email already exists
      const existing = await env.DB.prepare('SELECT id FROM waitlist WHERE email = ?')
        .bind(normalizedEmail)
        .first();

      if (existing) {
        return jsonResponse(
          {
            success: true,
            message: "You're already on the waitlist!",
          },
          200,
          corsHeaders
        );
      }

      // Insert new entry
      await env.DB.prepare(
        'INSERT INTO waitlist (email, created_at, user_agent, referrer) VALUES (?, ?, ?, ?)'
      )
        .bind(
          normalizedEmail,
          new Date().toISOString(),
          request.headers.get('User-Agent') || '',
          request.headers.get('Referer') || ''
        )
        .run();
    } else if (env.WAITLIST_KV) {
      // KV fallback - use email as key
      const key = `email:${normalizedEmail}`;
      const existing = await env.WAITLIST_KV.get(key);

      if (existing) {
        return jsonResponse(
          {
            success: true,
            message: "You're already on the waitlist!",
          },
          200,
          corsHeaders
        );
      }

      await env.WAITLIST_KV.put(
        key,
        JSON.stringify({
          email: normalizedEmail,
          created_at: new Date().toISOString(),
          user_agent: request.headers.get('User-Agent') || '',
          referrer: request.headers.get('Referer') || '',
        })
      );

      // Add to list for counting
      const listData = (await env.WAITLIST_KV.get('email_list')) || '[]';
      const list = JSON.parse(listData);
      list.push(normalizedEmail);
      await env.WAITLIST_KV.put('email_list', JSON.stringify(list));
    }

    return jsonResponse(
      {
        success: true,
        message: 'Successfully joined the waitlist!',
      },
      200,
      corsHeaders
    );
  } catch {
    return jsonResponse({ error: 'Failed to save email' }, 500, corsHeaders);
  }
}

async function handleStats(request, env, corsHeaders) {
  // Simple auth check - should use proper auth in production
  const authToken = request.headers.get('Authorization');
  if (authToken !== `Bearer ${env.ADMIN_TOKEN}`) {
    return jsonResponse({ error: 'Unauthorized' }, 401, corsHeaders);
  }

  try {
    let count = 0;

    if (env.DB) {
      const result = await env.DB.prepare('SELECT COUNT(*) as count FROM waitlist').first();
      count = result?.count || 0;
    } else if (env.WAITLIST_KV) {
      const listData = (await env.WAITLIST_KV.get('email_list')) || '[]';
      count = JSON.parse(listData).length;
    }

    return jsonResponse({ count }, 200, corsHeaders);
  } catch (error) {
    return jsonResponse({ error: 'Failed to get stats' }, 500, corsHeaders);
  }
}

async function handleExport(request, env, corsHeaders) {
  // Simple auth check
  const authToken = request.headers.get('Authorization');
  if (authToken !== `Bearer ${env.ADMIN_TOKEN}`) {
    return jsonResponse({ error: 'Unauthorized' }, 401, corsHeaders);
  }

  try {
    let emails = [];

    if (env.DB) {
      const results = await env.DB.prepare(
        'SELECT email, created_at FROM waitlist ORDER BY created_at DESC'
      ).all();
      emails = results.results || [];
    } else if (env.WAITLIST_KV) {
      const listData = (await env.WAITLIST_KV.get('email_list')) || '[]';
      const list = JSON.parse(listData);
      emails = list.map((email) => ({ email, created_at: 'N/A' }));
    }

    // Generate CSV
    const csv = ['Email,Created At', ...emails.map((e) => `"${e.email}","${e.created_at}"`)].join(
      '\n'
    );

    return new Response(csv, {
      headers: {
        ...corsHeaders,
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename="waitlist.csv"',
      },
    });
  } catch (error) {
    return jsonResponse({ error: 'Failed to export' }, 500, corsHeaders);
  }
}

function isValidEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

function jsonResponse(data, status = 200, corsHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      ...corsHeaders,
      'Content-Type': 'application/json',
    },
  });
}
