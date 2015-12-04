@app.route('/complete_paypal/<cart_id>', methods=['GET', 'POST'])
def paypal_complete(cart_id):
    logger.debug('Handling completion')
    try:
        cart = Enrollment.objects.get(id=cart_id)
    except Enrollment.DoesNotExist:
        logger.error('paypal_complete() no cart: %s' % cart_id)
        flash(messages.FLASH_PAYMENT_FAILED)
        return abort(404)

    session['cart_id'] = cart_id
    db_log = Member.objects.get_db_logger(target_user=cart.contact)

    try:
        handle_paypal_complete(cart, request.args['token'], request.args['PayerID'])
    except CheckoutException, e:
        db_log.paypal_complete_exception(cart, description=unicode(e))

        redirect_url = session['paypal_redirect_url']

        if str(e.errorcode) == "10486" and redirect_url:
            # redirect buyer to PayPal url again

            redirect_count = session.get('paypal_redirect_counter', 0) + 1
            session['paypal_redirect_counter'] = redirect_count
            if redirect_count < 3:
                logger.warning('PAYPAL: redirecting to %s due to code 10486. '
                               'cart_id=%s. redirect_counter=%s',
                               redirect_url, cart_id, redirect_count)
                try:
                    return redirect(redirect_url)
                except Exception, e:
                    logger.error('PAYPAL: error during redirect to %s: %s',
                                 redirect_url, e)
                    flash(messages.FLASH_PAYPAL_ISSUE)

            else:  # redirect_count >= 3
                flash(messages.FLASH_PAYPAL_ISSUE)
        else:
            session.pop('paypal_redirect_counter', None)
            logger.error('Failed to complete paypal transaction for order: %s:" % cart.id)
            logger.error('message=%s apierror=%s errorcode=%s", e.message, e.apierror, e.errorcode)
            flash('%s \n\nPAYPAL error message: %s' % (e.message, e.apierror))
    except Exception, e:
        db_log.paypal_complete_failed(cart, description=unicode(e))
        logger.error('Error handling cart update: %s' % e)
        flash(messages.FLASH_PAYMENT_FAILED)
    else:
        db_log.paypal_complete(cart)

        session.pop('paypal_redirect_url', None)
        session.pop('paypal_redirect_counter', None)
    flash('\n\n%s' % messages.FLASH_ENROLLMENT_INFORMATION_REMINDER % url_for('account_family', app_root='connect'))
    return redirect('/connect/register/select_programs')
