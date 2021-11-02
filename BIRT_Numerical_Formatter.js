/*   
  BIRT Numerical Formatter
  v1.0 Matt Gracz -- 11/1/2021
  
  =======================================================================================================
  NOTE: This script is designed to be able to be used by non-programmer BIRT users.  Just be sure to follow
        the Instructions for use below very carefully.  An aside for programmers can be found at the bottom 
        of this script.
  ========================================================================================================

*/

/*
   SCRIPT USAGE:

   Use case 1:
   Sometimes BIRT's currency converstion algorithm for formatted display in data fields in the outline tab
   straight up fails by displaying the inputted number entirely unformatted.

   In that case, change the corresponding data field's type to "String" and utilitize this code to do a 
   basic USD currency formatted display. If your currency isn't USD or if you need some other special unit,
   see Use Case 2.

   Use case 2:
   This code handles formatting of comma-separated USD numbers (like  $ 123,345.78) but also with no unit, or 
   other non-USD currencies, or a percent sign, or any other case where you need custom text displayed before 
   and/or after a comma'd number in BIRT for which BIRT can't handle the display natively or does so clumsily.

   Examples:
       1,345 GSF
       *** 123,456.23432432 ***
       34.23%

   The sky is the limit, so long as you are wrapping your custom text around a comma'd number in BIRT.

   NOTE: Converting to percent is supported by this script already.  Just use convertToPercent in Step 6

 
   =====Instructions for use=====
   Steps:
   1. Navigate to the script tab of the top-most object in the report outline - it's the item whose name is the
      report filename.
   2. In the Script event drop down near the top of the viewing pane make sure "initialize" is selected.
   3. In the script tab's text editor, insert the code between the barred hyphens below.  If you have other
      code there already, make sure not to blow away your old code when pasting this one in.
   4. Navigate to the Edit Data Binding window of the item whose currency display is failing. (typically by 
      double-clicking the data element in the layout tab)
   5. Change the Data Type to String
   6. Depending on your needs, change the Expression to:

                      convertToDollars(dataSetRow["Column Name"]);
                    or
                      convertToPercent(dataSetRow[Available_Data_binding])
                  etc...

    7. If you don't need USD or percent, then you'll need to copy and paste this in instead and fill in the text between
       the brackets with the appropriate values:

            convertToCommaFormat(["Column Name" or Available_Data_binding],
                                 [text that goes in front of the number],
                                 [text that goes after the number],
                                 [number of decimal places],
                                 [pad with a space on both ends? Valid answers: yes|true|false|no]);

            NOTE: padding sometimes improves BIRT's display of strings returned by the script

   8. Repeat steps 4-7 for any other report elements who misbehave similarly.


 */

 /* ================================================================================================ */
 /* ================================================================================================ */
 /* ================================================================================================ */
function convertToCommaFormat(in_s, leading_string, trailing_string, precision, padYesNo) {
  /* make sure in_s is a string; gotta handle possible int/float primitives passed in */
    var s = in_s.toString();
    var decIdx = s.indexOf(".");

    /* process lhs first */
    /* withoutDec: the numbers left of the decimal, if any */
    var withoutDec = s.substring(0, decIdx == -1 ? s.length : decIdx);
    /* stepSize: the number of digits between commas.  E.g., we write 112,345 not 11,2345*/
    var stepSize = 3;
    /* withCommas: the fully comma'd lhs that is a component of the final return value */
    var withCommas = "";
    var len = withoutDec.length;
    /* algorithm: place a "cursor" directly to the left of the decimal point, then crawl
       left-to-right, inserting a comma every stepSize number of digits */
    if (len > stepSize) {
        for(var anchor = len; anchor > stepSize; anchor -= stepSize) {
            var cursor = anchor - stepSize;
            var commaStr = ","+withoutDec.substring(cursor, anchor);
            withCommas = commaStr + withCommas;
        }
        /* at the end, handle strings who's lengths aren't multiples of stepSize */
        withCommas = withoutDec.substring(0, anchor) + withCommas;
    }
    else {
        /* not enough numbers to the left of the decimal to insert any commas */
        withCommas = withoutDec;
    }

    /* process rhs */
    /* logic: handle each case of the rhs piecewise:
              a) Set the string to nothing if:
                     precision == 0
              b) Set the string to .0*precision if:
                     number of decimal values present is 0 or no decimal point is present
              c) Set the string to rhs+0*(precision-rhs.length) if:
                     number of decimal values present < precision
              d) Set the string to rhs[0,precision] if:
                     number of decimal values present > precision
              e) Set the string to the passed-in rhs, i.e., "do nothing" if:
                     number of decimal values present == precision

    */
    var decimalPiece = "";
    if(precision > 0) {
        var decimalPiece = (decIdx == -1 || decIdx == s.length-1) ? "0".repeat(precision) : s.substring(decIdx+1, decIdx+precision+1);
        if(decimalPiece.length < precision) {
          decimalPiece = decimalPiece + "0".repeat(precision - length);
        }
        else if(decimalPiece.lenth > precision) {
          decimalPiece = decimalPiece.substring(0, precision);
        }
        decimalPiece = "." + decimalPiece;
    }

    /* NOTE: padding sometimes improves BIRT's display of strings returned by the script */
    var finalString =  leading_string + withCommas + decimalPiece + trailing_string;
    return padYesNo.toLowerCase() != "no" && (padYesNo || padYesNo.toLowerCase() == "yes") ? " " + finalString + " " : finalString;
}

function convertToDollars(in_s) { return convertToCommaFormat(in_s, "$ ", "", 2, true); }
function convertToTrailingDollars(in_s) { return convertToCommaFormat(in_s, "", " $", 2, true)}
function convertToPercent(in_s) { return convertToCommaFormat(in_s, "", "%", 2, true)}

reportContext.setPersistentGlobalVariable("convertToCommaFormat", convertToCommaFormat);
reportContext.setPersistentGlobalVariable("convertToCommaFormat", convertToDollars);
reportContext.setPersistentGlobalVariable("convertToCommaFormat", convertToTrailingDollars);
/* ================================================================================================ */
/* ================================================================================================ */
/* ================================================================================================ */






/* FOR PROGRAMMER'S INTERESTS ONLY:
   Table of Contents:
   1) Unit Tests
   2) Methodology Justification

/*  
   1) FOR TESTING IN AN EXTERNAL ENGINE:

   The following testing code is executable in any es6+ engine, e.g., mozilla's:

                https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/map
 */
var testSuite = [[convertToDollars, 1500.234," $ 1,500.23 "],
                 [convertToDollars, 123345678.123," $ 123,345,678.12 "],
                 [convertToDollars, 123," $ 123.00 "],
                 [convertToDollars, 34.," $ 34.00 "],
                 [convertToDollars, .893, " $ .89 "]
                 [convertToDollars, 1456743980," $ 1,456,743,980.00 "],
                 [convertToDollars, 458754.456," $ 458,754.45 "],
                 [convertToTrailingDollars, 123.456," 123.45 $ "],
                 [convertToTrailingDollars, 123.67," 123.67 $ "],
                 [convertToTrailingDollars, 34.," 34.00 $ "],
                 [convertToTrailingDollars, 4.04," 4.04 $ "],
                 [convertToTrailingDollars, 3," 3.00 $ "],
                 [convertToPercent, 4, " 4.00% "],
                 [convertToPercent, 345.789, " 345.78% "],
                 [convertToPercent, .312, " .312%"]
                 [convertToPercent, 2., " 2.00% "]];

console.log(testSuite.map(test => test[0](test[1])==test[2]));

/*
   2) An aside to fellow programmers:
   There are more concise algs and APIs and libs out there that do this same thing, but what makes this unique
   to BIRT is it is done using *only* the most universally-available symbols in almost all versions of javascript,
   i.e., int and string primitives, their properties, and their methods.  So no matter what weird or archaic
   BIRT engine you stick this code in, it will work as intended. Any mods you could make with e.g., objects, even
   simple ones like arrays, can cause this code to not work in BIRT versions without those esX-dependendent
   objects.  Same goes with code flow: I used only ifs and for-loops; no fancy inline funcs and the like.

   It is also more flexible than most off-the-shelf solutions out there in the variety of strings it can output,
   when paramaterized correctly.
 */