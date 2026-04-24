export default async function handler(req, res) {
    if (req.method !== 'POST') {
        return res.status(405).json({ error: 'Method not allowed' });
    }

    const { email } = req.body;

    if (!email || !email.includes('@') || !email.includes('.')) {
        return res.status(400).json({ error: 'Invalid email address' });
    }

    try {
        const response = await fetch(
            'https://api.beehiiv.com/v2/publications/pub_719cc28f-91a4-4a1a-9b6b-016767538d3a/subscriptions',
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${process.env.BEEHIIV_API_KEY}`
                },
                body: JSON.stringify({
                    email: email,
                    reactivate_existing: false,
                    send_welcome_email: false,
                    utm_source: 'waitlist',
                    utm_medium: 'organic'
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            return res.status(response.status).json({ error: data.message || 'Subscription failed' });
        }

        return res.status(200).json({ success: true });
    } catch (err) {
        return res.status(500).json({ error: 'Internal server error' });
    }
}
