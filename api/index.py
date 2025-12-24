name: Metal Price Tracker v2.0

on:
  schedule:
    # Her gÃ¼n sabah 7:00'den akÅŸam 21:00'a kadar her 30 dakikada bir
    # 04:00-18:00 UTC = 07:00-21:00 TÃ¼rkiye saati (UTC+3)
    - cron: '0,30 4-18 * * *'
    
    # Gece optimizasyon iÅŸi - her gece 02:00 TÃ¼rkiye saati
    # 23:00 UTC = 02:00 TÃ¼rkiye saati (UTC+3)
    - cron: '0 23 * * *'
    
  workflow_dispatch: # Manuel tetikleme iÃ§in

jobs:
  metal-tracker:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
      
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        
    - name: Install dependencies
      run: |
        pip install requests beautifulsoup4
        
    - name: Create data directory
      run: |
        mkdir -p data
        
    - name: Determine operation based on time
      run: |
        # TÃ¼rkiye saati hesapla (UTC+3)
        TURKEY_HOUR=$(date -u -d '+3 hours' +%H)
        TURKEY_MINUTE=$(date -u -d '+3 hours' +%M)
        CURRENT_UTC_HOUR=$(date -u +%H)
        
        echo "ðŸ• UTC Saati: $(date -u +%H:%M)"
        echo "ðŸ‡¹ðŸ‡· TÃ¼rkiye Saati: $TURKEY_HOUR:$TURKEY_MINUTE"
        echo "ðŸ“… Tarih: $(date -u -d '+3 hours' +%Y-%m-%d)"
        
        # Gece optimizasyon kontrolÃ¼ (02:00 TÃ¼rkiye saati)
        if [ $TURKEY_HOUR -eq 2 ]; then
          echo "ðŸŒ™ Gece optimizasyonu zamanÄ± - baÅŸlatÄ±lÄ±yor..."
          python scripts/price_tracker.py --optimize
          
        # Veri toplama saatleri kontrolÃ¼ (07:00-21:00 TÃ¼rkiye saati)
        elif [ $TURKEY_HOUR -ge 7 ] && [ $TURKEY_HOUR -lt 21 ]; then
          echo "ðŸ“Š Veri toplama saatleri ($TURKEY_HOUR:$TURKEY_MINUTE) - baÅŸlatÄ±lÄ±yor..."
          python scripts/price_tracker.py --collect
          
        else
          echo "â° Belirlenen saatler dÄ±ÅŸÄ±nda ($TURKEY_HOUR:$TURKEY_MINUTE)"
          echo "   ðŸ“Š Veri toplama: 07:00-21:00 TR"
          echo "   ðŸŒ™ Optimizasyon: 02:00 TR"
          echo "   âŒ Ä°ÅŸlem yapÄ±lmÄ±yor"
          exit 0
        fi
        
    - name: Commit and push changes
      run: |
        git config --local user.email "action@github.com"
        git config --local user.name "Metal Tracker Bot v2.0"
        
        # DeÄŸiÅŸiklik varsa commit et
        if [ -f data/price-history.json ]; then
          git add data/price-history.json
          
          # Commit mesajÄ±nÄ± operasyona gÃ¶re belirle
          TURKEY_HOUR=$(date -u -d '+3 hours' +%H)
          
          if [ $TURKEY_HOUR -eq 2 ]; then
            COMMIT_MSG="ðŸŒ™ Daily optimization: $(date -u -d '+3 hours -1 day' +%Y-%m-%d) peak data saved"
          else
            COMMIT_MSG="ðŸ“Š Price update: $(date -u -d '+3 hours' +%Y-%m-%d\ %H:%M) TR"
          fi
          
          # Sadece deÄŸiÅŸiklik varsa commit yap
          git diff --staged --quiet || (
            echo "ðŸ’¾ Committing changes: $COMMIT_MSG"
            git commit -m "$COMMIT_MSG"
            git push
          )
        else
          echo "âŒ No data file found - skipping commit"
        fi
        
    - name: Print operation summary
      run: |
        TURKEY_HOUR=$(date -u -d '+3 hours' +%H)
        echo ""
        echo "ðŸ“‹ Ä°ÅŸlem Ã–zeti:"
        echo "==============="
        
        if [ $TURKEY_HOUR -eq 2 ]; then
          echo "ðŸŒ™ Gece optimizasyonu tamamlandÄ±"
          echo "   â€¢ Bir Ã¶nceki gÃ¼nÃ¼n peak deÄŸeri saklandÄ±"
          echo "   â€¢ DiÄŸer veriler temizlendi"
        else
          echo "ðŸ“Š Veri toplama tamamlandÄ±"
          echo "   â€¢ AltÄ±n fiyatÄ± Ã§ekildi"
          echo "   â€¢ GÃ¼mÃ¼ÅŸ fiyatÄ± Ã§ekildi"
          echo "   â€¢ PortfÃ¶y deÄŸeri hesaplandÄ±"
        fi
        
        echo ""
        echo "â° Bir sonraki Ã§alÄ±ÅŸma:"
        if [ $TURKEY_HOUR -eq 2 ]; then
          echo "   ðŸ“Š 07:00 TR (Veri toplama baÅŸlangÄ±cÄ±)"
        elif [ $TURKEY_HOUR -ge 20 ]; then
          echo "   ðŸŒ™ 02:00 TR (Gece optimizasyonu)"
        else
          echo "   ðŸ“Š $(($TURKEY_HOUR + 1)):00 TR (Veri toplama devam)"
        fi
        
        echo ""
        echo "âœ… Workflow baÅŸarÄ±yla tamamlandÄ±!"