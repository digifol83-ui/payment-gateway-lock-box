/**
 * BeastPay Wallet Connector Plugin
 * Manages wallet selection and persistence across checkout flows
 *
 * Usage:
 *   const wallet = WalletConnector.getWallet()
 *   WalletConnector.setWallet('metamask', '0x0582b74D10c853B52335542036e6CEA9B780849A')
 */

class WalletConnector {
  static STORAGE_KEY = 'beastpay_wallet_connector'
  static DEFAULT_WALLET = {
    type: 'metamask',
    address: '0x0582b74D10c853B52335542036e6CEA9B780849A',
    name: 'BeastPay MetaMask (BNB USDT)',
    network: 'bsc',
    isDefault: true,
  }

  /**
   * Get stored wallet configuration
   * Returns default if none stored
   */
  static getWallet() {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY)
      if (stored) {
        return JSON.parse(stored)
      }
    } catch (e) {
      console.warn('Failed to parse stored wallet:', e)
    }
    return this.DEFAULT_WALLET
  }

  /**
   * Set wallet configuration
   */
  static setWallet(type, address, metadata = {}) {
    const wallet = {
      type,
      address,
      name: metadata.name || `${type.charAt(0).toUpperCase() + type.slice(1)} Wallet`,
      network: metadata.network || 'ethereum',
      isDefault: metadata.isDefault || false,
      lastUpdated: new Date().toISOString(),
    }
    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(wallet))
    return wallet
  }

  /**
   * Clear stored wallet (revert to default)
   */
  static clear() {
    localStorage.removeItem(this.STORAGE_KEY)
  }

  /**
   * Initialize wallet selector UI
   * Attaches event listeners to wallet selector elements
   */
  static initializeUI() {
    const wallet = this.getWallet()

    // Display current wallet
    const walletDisplay = document.getElementById('walletDisplay')
    if (walletDisplay) {
      walletDisplay.textContent = `${wallet.name} (${wallet.address.slice(0, 6)}...${wallet.address.slice(-4)})`
    }

    // Attach change handler
    const walletSelect = document.getElementById('walletSelect')
    if (walletSelect) {
      walletSelect.value = wallet.type
      walletSelect.addEventListener('change', (e) => {
        // Route to wallet-specific page or modal
        window.location.href = `/wallet-manager?type=${e.target.value}`
      })
    }
  }

  /**
   * Validate wallet address format
   */
  static isValidAddress(address, network = 'ethereum') {
    if (!address) return false

    // Ethereum/BSC addresses
    if (network === 'ethereum' || network === 'bsc') {
      return /^0x[a-fA-F0-9]{40}$/.test(address)
    }

    // Add other networks as needed
    return false
  }

  /**
   * Get URL-safe wallet string for payment links
   */
  static getWalletParam() {
    const wallet = this.getWallet()
    return encodeURIComponent(wallet.address)
  }
}

// Auto-initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => WalletConnector.initializeUI())
} else {
  WalletConnector.initializeUI()
}
