<?php
    include 'modules/names.php';                              // Variablen mit Strings
    include 'modules/database.php';                           // Schnittstelle zur Datenbank
    include 'modules/logging.php';                            //liest die Datei fuer das logging ein
    
    if(isset ($_POST['scale_wizzard'])) {
        $scale = $_POST['scale_wizzard_radiobutton'];
        if ($scale == $scale1_key){
            $scale_number = 1;
            $scale_status = $status_scale1_key;
            $scale_calibrate = $calibrate_scale1_key;   
        }
        else{
            $scale_number = 2;
            $scale_status = $status_scale2_key;
            $scale_calibrate = $calibrate_scale2_key;
        }
        write_stop_in_database($scale_status);
        $logstring = _('measuring scale stopped'). ' ' . _('scale'). ' ' . $scale_number . ' ' . 'due to calibrating scale';
        logger('INFO', $logstring);
        write_start_in_database($scale_calibrate);
        $logstring = _('starting calibrate'). ' ' . _('scale'). ' ' . $scale_number;
        logger('INFO', $logstring);
        $scale_calibrate_status = 1;
        while ($scale_calibrate_status != 2) {
            $scale_calibrate_status = get_calibrate_status($scale_calibrate);
            sleep(1);
            write_startstop_status_in_database($scale_calibrate, 2);
            // Python misst jetzt den Wert mit der Refunit = 1
        }
        if ($scale_calibrate_status == 2){
        // Seite aufbauen mit Button und eingabe von Gewicht in Gramm
            include 'header.php';                                     // Template-Kopf und Navigation
            echo '<h2 class="art-postheader">' . strtoupper(_('scale wizzard')) . '</h2>';
            echo '<div class="hg_container">';
            echo _('Please attach a known weight to the loadcell'). ' ' . $scale_number . ' ' . _('now and enter the weight into the form below:'). '<br><br>';
            echo '<form action="/modules/calibrate_scale.php" method="post">';
            echo _('weight') . '<input type="number" name="scale_wizzard_weight" required> ' . _('gram') . '<br><br>';
            echo '<input type="hidden" name="scale_number" type="text" value="'. $scale_number . '">';
            echo '<button class="art-button" name="scale_wizzard2" value="scale_wizzard2"  onclick="return confirm("' ._('weight attatched'). '?");">'._('weight attatched'). '</button>';
            echo '<button class="art-button" name="scale_wizzard_cancel"  formnovalidate formaction="settings.php" onclick="return confirm("' ._('cancel scale wizzard?'). '?");">'._('cancel'). '</button>';
            echo '</form>';
            echo '</div>';
            echo '</div></div></div></div></div></div>';
            include 'footer.php';
        }
    }
    else{
        print '<script language="javascript"> alert("'. (_("scale wizzard")) . " : " . (_("no scale selected")) .'"); window.location.href = "settings.php";</script>';
    }
?>