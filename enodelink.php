<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);

$error = '';
$redirectUrl = '';
$linkGenerated = false;
$environment = 'production'; // Default to production

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $clientId = $_POST['client_id'] ?? '';
    $clientSecret = $_POST['client_secret'] ?? '';
    $userId = $_POST['user_id'] ?? '7205ca66';
    $environment = $_POST['environment'] ?? 'production';
    
    try {
        if (empty($clientId) || empty($clientSecret)) {
            throw new Exception('Both Client ID and Secret are required');
        }

        $tokenResponse = getEnodeToken($clientId, $clientSecret, $environment);
        
        if (!isset($tokenResponse['access_token'])) {
            throw new Exception('Invalid token response');
        }

        $accessToken = $tokenResponse['access_token'];
        
        $linkResponse = generateEnodeLink($accessToken, $userId, $environment);
        
        if (isset($linkResponse['linkUrl'])) {
            $redirectUrl = $linkResponse['linkUrl'];
            $linkGenerated = true;
        } else {
            throw new Exception('No linkUrl in response');
        }
        
    } catch (Exception $e) {
        $error = $e->getMessage();
    }
}

function getBaseUrl($environment) {
    return $environment === 'production' 
        ? 'production.enode.io' 
        : 'sandbox.enode.io';
}

function getEnodeToken($clientId, $clientSecret, $environment) {
    $baseUrl = getBaseUrl($environment);
    $url = "https://oauth.$baseUrl/oauth2/token";
    
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_USERPWD, $clientId . ':' . $clientSecret);
    curl_setopt($ch, CURLOPT_POSTFIELDS, 'grant_type=client_credentials');
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/x-www-form-urlencoded'
    ]);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($httpCode !== 200) {
        throw new Exception('Failed to get access token');
    }
    
    $decoded = json_decode($response, true);
    if (!$decoded) {
        throw new Exception('Invalid token response format');
    }
    
    return $decoded;
}

function generateEnodeLink($accessToken, $userId, $environment) {
    $baseUrl = getBaseUrl($environment);
    $url = "https://enode-api.$baseUrl/users/$userId/link";
    
    $data = [
        'vendorType' => 'vehicle',
        'scopes' => [
            'vehicle:read:data',
            'vehicle:read:location',
            'vehicle:control:charging'
        ],
        'language' => 'en-US',
        'redirectUri' => 'https://localhost:3000'
    ];
    
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        "Authorization: Bearer $accessToken",
        "Content-Type: application/json"
    ]);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($httpCode !== 200) {
        throw new Exception('Failed to generate link');
    }
    
    $decoded = json_decode($response, true);
    if (!$decoded) {
        throw new Exception('Invalid link response format');
    }
    
    return $decoded;
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enode Link Generator</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 400px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .form-container {
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 20px;
            font-size: 24px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            width: 100%;
            padding: 12px;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 10px;
        }
        button[type="submit"] {
            background: #4CAF50;
        }
        .copy-button {
            background: #1976d2;
        }
        .open-button {
            background: #2e7d32;
        }
        button:hover {
            opacity: 0.9;
        }
        .error {
            color: #d32f2f;
            background: #ffebee;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 15px;
        }
        .success {
            color: #2e7d32;
            background: #e8f5e9;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 15px;
        }
        .generated-link {
            word-break: break-all;
            background: #f5f5f5;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
            font-family: monospace;
        }
        .info {
            font-size: 13px;
            color: #666;
            margin-top: 20px;
        }
        .radio-group {
            display: flex;
            gap: 15px;
            margin-bottom: 15px;
        }
        .radio-option {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .info ul {
            margin: 5px 0;
            padding-left: 20px;
        }
    </style>
</head>
<body>
    <div class="form-container">
        <h1>Enode Link Generator</h1>
        
        <?php if ($error): ?>
            <div class="error"><?php echo htmlspecialchars($error); ?></div>
        <?php endif; ?>
        
        <?php if ($linkGenerated && $redirectUrl): ?>
            <div class="success">
                <h3>Link Generated Successfully!</h3>
                <div class="generated-link"><?php echo htmlspecialchars($redirectUrl); ?></div>
                <button class="copy-button" onclick="copyLink()">Copy Link</button>
                <button class="open-button" onclick="window.open('<?php echo htmlspecialchars($redirectUrl); ?>', '_blank')">
                    Open in New Tab
                </button>
            </div>
            
            <script>
            function copyLink() {
                const linkText = `<?php echo htmlspecialchars($redirectUrl); ?>`;
                navigator.clipboard.writeText(linkText)
                    .then(() => alert('Link copied to clipboard!'))
                    .catch(err => alert('Failed to copy link: ' + err));
            }
            </script>
        <?php else: ?>
            <form method="POST" autocomplete="off">
                <div class="form-group">
                    <label for="client_id">Client ID</label>
                    <input type="text" id="client_id" name="client_id" required>
                </div>
                
                <div class="form-group">
                    <label for="client_secret">Client Secret</label>
                    <input type="password" id="client_secret" name="client_secret" required>
                </div>
                
                <div class="form-group">
                    <label for="user_id">User ID</label>
                    <input type="text" id="user_id" name="user_id" value="7205ca66">
                </div>
                
                <div class="form-group">
                    <label>Environment</label>
                    <div class="radio-group">
                        <div class="radio-option">
                            <input type="radio" id="prod" name="environment" value="production" <?php echo $environment === 'production' ? 'checked' : ''; ?>>
                            <label for="prod">Production</label>
                        </div>
                        <div class="radio-option">
                            <input type="radio" id="sandbox" name="environment" value="sandbox" <?php echo $environment === 'sandbox' ? 'checked' : ''; ?>>
                            <label for="sandbox">Sandbox</label>
                        </div>
                    </div>
                </div>
                
                <button type="submit">Generate Link</button>
            </form>
        <?php endif; ?>
        
        <div class="info">
            <strong>No Storage At All:</strong>
            <ul>
                <li>Credentials are only used for the API calls and never stored</li>
                <li>No cookies, sessions, or files are created</li>
                <li>All data disappears after the redirect</li>
            </ul>
        </div>
    </div>
</body>
</html>